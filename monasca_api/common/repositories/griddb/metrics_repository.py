# (C) Copyright 2017 Akira Yoshiyama <akirayoshiyama@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import collections
from datetime import datetime
import string

import griddb_python_client as griddb
from oslo_config import cfg
from oslo_log import log
from oslo_utils import timeutils

from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories import metrics_repository
from monasca_common.rest.utils import from_json

CONF = cfg.CONF
LOG = log.getLogger(__name__)

CONTAINER_NAME_CHARS = string.digits + string.ascii_letters + '_'

METRIC_PREFIX = "monasca_metric"
MEASUREMENT_PREFIX = "monasca_measure"
ALARM_STATE_HISTORY_PREFIX = "monasca_ash"

UNSIGNED_LONG_MASK = 0xffffffffffffffff

EPOCH_START = datetime(1970, 1, 1)


Metric = collections.namedtuple(
    "Metric",
    ["name", "map"]
)

Measurement = collections.namedtuple(
    "Measurement",
    ["timestamp", "metric_hash", "value", "value_meta"]
)

AlarmHistory = collections.namedtuple(
    "AlarmHistory",
    ["timestamp", "alarm_id", "metrics", "new_state", "old_state", "reason",
     "sub_alarms", "id"]
)


def to_hash_str(hash_long):
    """Convert a hash value in DB into a hex string

    :param hash_long: Hash value
    :type hash_long: int (64bit signed int)
    :return: Hash string
    :rtype: str or None
    """
    return hex(hash_long & UNSIGNED_LONG_MASK)[2:-1]


def to_hash_long(hash_str):
    """Convert a hash value in DB into a hex string

    :param hash_long: Hash value
    :type hash_long: int (64bit signed int)
    :return: Hash string
    :rtype: str or None
    """
    value = int(hash_str, 16)
    if value > 0x8000000000000000:
        value -= 0x10000000000000000
    return value


def from_timestamp_ms(timestamp_ms):
    """Stringify datetime in ISO 8601 format + millisecond.

    :param timestamp_ms: Timestamp with milliseconds
    :type timestamp_ms: int
    :return: ISO 8601-style date time
    :rtype: str
    """
    st = datetime.utcfromtimestamp(float(timestamp_ms) / 1000).isoformat()
    if '.' in st:
        st = st[:23] + 'Z'
    else:
        st += '.000Z'
    return st.decode('utf8')


def to_timestamp(date_time_string):
    """Make timestamp from ISO 8601 format.

    :param date_time_string: ISO 8601-style date time
    :type date_time_string: str
    :return: Timestamp in seconds
    :rtype: float
    """
    dt = timeutils.parse_isotime(date_time_string)
    dt = timeutils.normalize_time(dt)
    timestamp = (dt - EPOCH_START).total_seconds()
    return timestamp


def gsexception_handler(func):
    """Handle GSException of GridDB."""
    def _decorator(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except griddb.GSException as e:
            e.args += (str(e.what()),)
            LOG.exception(e)
            raise e
    return _decorator


def exception_handler(func):
    """Convert exceptions into RepositoryException."""
    def _decorator(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            LOG.exception(e)
            raise exceptions.RepositoryException(e)
    return _decorator


class MetricsRepository(metrics_repository.AbstractMetricsRepository):
    """Metric repository for GridDB."""

    @gsexception_handler
    def __init__(self):
        """Setup MetricsRepository object."""
        self.factory = griddb.StoreFactory.get_default()
        self.gridstore = self.factory.get_store({
            "notificationAddress": CONF.griddb.notification_address,
            "notificationPort": str(CONF.griddb.notification_port),
            "clusterName": CONF.griddb.cluster_name,
            "user": CONF.griddb.user,
            "password": CONF.griddb.password
        })

    @gsexception_handler
    def _get_container(self, *args):
        """Get a time series or a collection object of GridDB.

        :param args: tuple for the time series name
        :type args: list(str)
        :return: time series object
        :rtype: griddb.Container
        """
        name = "".join([_ for _ in "_".join(args)
                        if _ in CONTAINER_NAME_CHARS])
        LOG.debug("name: %s", name)
        try:
            # Get a time series container
            con = self.gridstore.get_container(name)

            # Check the container type (raises if 'container not found')
            con.get_type()

        except griddb.GSException as e:
            # Error code 140001 means 'container not found'.
            if e.get_code() == 140001:
                return None
            raise e

    @gsexception_handler
    def _get_metrics(self, tenant_id, region,
                     start_timestamp=None, end_timestamp=None,
                     name=None):
        """Get metrics in a measurement container.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :keyword start_timestamp: Starting timestamp in ms (not supported)
        :type start_timestamp: int
        :keyword end_timestamp: Ending timestamp in ms (not supported)
        :type end_timestamp: int
        :keyword name: Metric name
        :type name: str
        :return: Metrics dictionary
        :rtype: dict
        """
        # Query measurement records
        ts = self._get_container(METRIC_PREFIX, region, tenant_id)
        if ts is None:
            return {}

        query_string = "select *"
        filters = []
        if end_timestamp:
            end_timestamp_ms = int(end_timestamp * 1000)
            filters.append("TO_EPOCH_MS(timestamp) <= %d" % end_timestamp_ms)
        if name:
            filters.append("name = '%s'" % name)
        if filters:
            query_string += " where " + " and ".join(filters)
        query = ts.query(query_string)

        # Fetch query results
        rs = query.fetch(False)
        row = ts.create_row()

        # Store them into a list
        metrics = {}
        while rs.has_next():
            rs.get_next(row)
            _hash = to_hash_str(row.get_field_as_long(0))
            _name = row.get_field_as_string(1)
            _map = from_json(row.get_field_as_string(2))
            metrics[_hash] = Metric(_name, _map)

        return metrics

    @gsexception_handler
    def _get_measurements(self, tenant_id, region, metrics,
                          start_timestamp=None, end_timestamp=None):
        """Get measurements in a measurement container.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :param metrics: Metrics
        :type metrics: list(Metric)
        :keyword start_timestamp: Starting timestamp in milliseconds
        :type start_timestamp: int
        :keyword end_timestamp: Ending timestamp in milliseconds
        :type end_timestamp: int
        :return: Measurements list
        :rtype: list(namedtuple)
        """
        measurements = []
        time_series_list = []
        queries = []

        for metric_hash, metric in metrics.items():
            # Query measurement records
            LOG.debug("metric: %s", metric.name)
            ts = self._get_container(MEASUREMENT_PREFIX, region, tenant_id,
                                     metric.name)
            if ts is None:
                return []

            query_string = "select *"
            filters = []
            if start_timestamp:
                start_timestamp_ms = int(start_timestamp * 1000)
                filters.append("TO_EPOCH_MS(timestamp) >= %d" %
                               start_timestamp_ms)
            if end_timestamp:
                end_timestamp_ms = int(end_timestamp * 1000)
                filters.append("TO_EPOCH_MS(timestamp) <= %d" %
                               end_timestamp_ms)
            if metrics:
                filters.append("hash = %d" % to_hash_long(metric_hash))
                time_series_list.append(ts)
            query_string += " where " + " and ".join(filters)
            LOG.debug("query: %s", query_string)
            queries.append(ts.query(query_string))

        # Fetch query results
        self.gridstore.fetch_all(queries)
        for query in queries:
            rs = query.get_row_set()
            LOG.debug("rs: %s", rs)
            row = ts.create_row()

            # Store them into a list
            while rs.has_next():
                rs.get_next(row)
                measurement = Measurement(
                    row.get_field_as_timestamp(0),  # timestamp
                    to_hash_str(row.get_field_as_long(1)),  # hash
                    row.get_field_as_float(2),  # value
                    from_json(row.get_field_as_string(3))  # value_map
                )
                measurements.append(measurement)

        LOG.debug("query finished")
        return measurements

    @gsexception_handler
    def _get_alarm_histories(self, tenant_id,
                             start_timestamp=None, end_timestamp=None):
        """Get alarm histories in a alarm histories container.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :keyword start_timestamp: Starting timestamp in milliseconds
        :type start_timestamp: int
        :keyword end_timestamp: Ending timestamp in milliseconds
        :type end_timestamp: int
        :return: Alarm histories list
        :rtype: list(namedtuple)
        """
        # Query alarm history records
        ts = self._get_container(ALARM_STATE_HISTORY_PREFIX, tenant_id)
        if ts is None:
            return []

        query_string = "select *"
        time_cond = []
        if start_timestamp:
            start_timestamp_ms = int(start_timestamp * 1000)
            time_cond.append("TO_EPOCH_MS(timestamp) >= %d" % start_timestamp_ms)
        if end_timestamp:
            end_timestamp_ms = int(end_timestamp * 1000)
            time_cond.append("TO_EPOCH_MS(timestamp) <= %d" % end_timestamp_ms)
        if time_cond:
            query_string += " where " + " and ".join(time_cond)
        query = ts.query(query_string)

        # Fetch query results
        rs = query.fetch(False)
        row = ts.create_row()

        # Store them into a list
        alarm_histories = []
        while rs.has_next():
            rs.get_next(row)
            alarm_history = AlarmHistory(
                row.get_field_as_timestamp(0),  # timestamp
                row.get_field_as_string(1),  # alarm_id
                from_json(row.get_field_as_string(2)),  # metrics
                row.get_field_as_string(3),  # new_state
                row.get_field_as_string(4),  # old_state
                row.get_field_as_string(5),  # reason
                from_json(row.get_field_as_string(6)),  # sub_alarms
                row.get_field_as_float(7)  # id
            )
            alarm_histories.append(alarm_history)

        return alarm_histories

    @exception_handler
    def list_metrics(self, tenant_id, region, name, dimensions, offset,
                     limit, start_timestamp=None, end_timestamp=None,
                     include_metric_hash=False):
        """Get metrics list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :param dimensions: Searching conditions
        :type dimensions: dict or None
        :param offset: ID of the starting record
        :type offset: str
        :param limit: Max number of records
        :type limit: int
        :keyword start_timestamp: Starting timestamp in ms (not supported)
        :type start_timestamp: int
        :keyword end_timestamp: Ending timestamp in ms (not supported)
        :type end_timestamp: int
        :return: Metrics list
        :rtype: list(dict)
        """
        # Get metrics
        metrics = self._get_metrics(tenant_id, region, name=name)

        # Filter metrics with dimensions and name
        if isinstance(dimensions, dict):
            for d_key, d_value in dimensions.items():
                d_values = d_value.split("|") if d_value else None

                new_metrics = {}
                for _hash, metric in metrics.items():
                    if d_key not in metric.map:
                        break
                    if d_values is None or metric.map[d_key] in d_values:
                        new_metrics[_hash] = metric
                metrics = new_metrics

        metric_list = []
        for _hash in sorted(metrics.keys()):
            metric_list.append((_hash, metrics[_hash].name, metrics[_hash].map))

        # Filter metrics with offset
        if offset is not None:
            if offset not in metrics:
                return []
            for index, metric in enumerate(metric_list):
                if offset == metric[0]:
                    metric_list = metric_list[index:]
                    break

        # Limit record number of metrics
        if limit is not None:
            metric_list = metric_list[:limit]

        result = []
        for _hash, _name, _map in metric_list:
            metric_map = {
                "id": _hash,
                "dimensions": _map
            }
            if _name is not None:
                metric_map["name"] = _name
            if include_metric_hash:
                metric_map["metric_hash"] = _hash
            result.append(metric_map)

        return result

    @exception_handler
    def list_metric_names(self, tenant_id, region, dimensions):
        """Get metric names list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :param dimensions: Searching conditions
        :type dimensions: dict or None
        :return: Metric names list
        :rtype: list(dict)
        """
        # Get metric list
        metrics = self._get_metrics(tenant_id, region).values()

        # Check dimensions is None
        if dimensions is None:
            dimensions = {}

        # Filter metrics with dimensions
        metric_names_list = set()
        for metric in metrics:
            for d_key, d_value in dimensions.items():
                if metric.map.get(d_key, '__NO_SUCH_VALUE__') != d_value:
                    break
            else:
                metric_names_list.add(metric.name)

        return [{'name': mn} for mn in metric_names_list]

    @exception_handler
    def list_dimension_names(self, tenant_id, region, metric_name):
        """Get dimension names list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :param metric_name: Metric name
        :type metric_name: str or None
        :return: Dimensions list
        :rtype: list(dict)
        """
        # Get metric list
        metrics = self._get_metrics(tenant_id, region,
                                    name=metric_name).values()

        # Filter metrics with metric_name
        dimension_names_list = set()
        for metric in metrics:
            dimension_names_list.update(metric.map.keys())

        return [{'dimension_name': dn} for dn in dimension_names_list]

    @exception_handler
    def list_dimension_values(
            self, tenant_id, region, metric_name, dimension_name):
        """Get dimension values list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :param metric_name: Metric name
        :type metric_name: str or None
        :param dimension_name: Searching conditions
        :type dimension_name: dict or None
        :type end_timestamp: int
        :return: Metrics list
        :rtype: list(dict)
        """
        # Get metric list
        metrics = self._get_metrics(tenant_id, region,
                                    name=metric_name).values()

        # Filter metrics with dimension_name
        dimension_values_list = set()
        for metric in metrics:
            value = metric.map.get(dimension_name)
            if value:
                dimension_values_list.add(metric.map[dimension_name])

        return [{'dimension_value': dv} for dv in dimension_values_list]

    @exception_handler
    def measurement_list(self, tenant_id, region, name, dimensions,
                         start_timestamp, end_timestamp, offset,
                         limit, merge_metrics_flag, group_by):
        """Get measurements list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :param name: Metric name
        :type name: str
        :param dimensions: Searching conditions
        :type dimensions: dict or None
        :param start_timestamp: Starting timestamp in milliseconds
        :type start_timestamp: int
        :param end_timestamp: Ending timestamp in milliseconds
        :type end_timestamp: int
        :param offset: ID of the starting record
        :type offset: str
        :param limit: Max number of records
        :type limit: int
        :param merge_metrics_flag: Whether multiple metrics are allowed
        :type merge_metrics_flag: bool
        :param group_by: Grouping factor (not supported now)
        :type group_by: list(str)
        :return: Metrics list
        :rtype: list(dict)
        """
        if offset is not None:
            offset_timestamp = to_timestamp(offset)
            if offset_timestamp > start_timestamp:
                start_timestamp = offset_timestamp

        LOG.debug("start_timestamp: %s (%s)", start_timestamp, type(start_timestamp))

        # Get metrics
        metrics = self._get_metrics(tenant_id, region, name=name)

        # Check dimensions is None
        if isinstance(dimensions, dict):

            # Filter measurements with dimensions and metric name
            for d_key, d_value in dimensions.items():
                d_values = d_value.split("|") if d_value else None

                new_metrics = {}
                for metric_hash, metric in metrics.items():
                    LOG.debug("metric: %s", metric)
                    if d_key not in metric.map:
                        break
                    if d_values is None or metric.map[d_key] in d_values:
                        new_metrics[metric_hash] = metric
                metrics = new_metrics

        # Get measurements
        measurements = self._get_measurements(tenant_id, region, metrics,
                                              start_timestamp=start_timestamp,
                                              end_timestamp=end_timestamp)

        # Limit record number
        if limit is not None:
            measurements = measurements[:limit]

        # Check whether measurement list has no entry
        if len(measurements) == 0:
            return []

        # Handle group-by
        measurements_per_groups = {}
        if group_by:
            for m in measurements:
                metric = metrics.get(m.metric_hash)
                if metric:
                    groups = tuple([metric.map.get(g) for g in group_by])
                    if None in groups:
                        return []
                    measurements_per_groups.setdefault(groups, [])
                    measurements_per_groups[groups].append(m)
        else:
            measurements_per_groups[tuple()] = measurements

        # Check whether multiple metrics are in
        for groups, measurements in measurements_per_groups.items():
            metric_hashes = set([m.metric_hash for m in measurements])
            if len(metric_hashes) > 1 and not merge_metrics_flag:
                raise exceptions.MultipleMetricsException(
                    self.MULTIPLE_METRICS_MESSAGE)

        # Prepare the result
        result = []
        for groups, measurements in measurements_per_groups.items():
            measurements_list = [
                (from_timestamp_ms(m.timestamp), m.value, m.value_meta)
                for m in measurements]

            # Handle group-by
            if groups:
                dimensions = {key: value
                              for key, value in zip(group_by, groups)}

            result.append({
                u'name': name,
                u'id': measurements_list[-1][0],
                u'dimensions': dimensions,
                u'columns': [u'timestamp', u'value', u'value_meta'],
                u'measurements': measurements_list})

        # Put the result
        return result

    @exception_handler
    def metrics_statistics(self, tenant_id, region, name, dimensions,
                           start_timestamp, end_timestamp, statistics,
                           period, offset, limit, merge_metrics_flag,
                           group_by):
        """Get measurement stats list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :param name: Metric name
        :type name: str
        :param dimensions: Searching conditions
        :type dimensions: dict or None
        :param start_timestamp: Starting timestamp in milliseconds
        :type start_timestamp: int
        :param end_timestamp: Ending timestamp in milliseconds
        :type end_timestamp: int
        :param statistics: List of statistics types
        :type statistics: list(str)
        :param period: Aggregation period in seconds
        :type period: int
        :param offset: ID of the starting record
        :type offset: str
        :param limit: Max number of records
        :type limit: int
        :param merge_metrics_flag: Whether multiple metrics are allowed
        :type merge_metrics_flag: bool
        :param group_by: Grouping factor (not supported now)
        :type group_by: list(str)
        :return: Metrics list
        :rtype: list(dict)
        """
        if not period:
            period = 300
        period = int(period)

        if offset is not None:
            offset_timestamp = to_timestamp(offset)
            if offset_timestamp > start_timestamp:
                start_timestamp = offset_timestamp

        # Get metrics
        metrics = self._get_metrics(tenant_id, region, name=name)

        # Check dimensions is None
        if isinstance(dimensions, dict):

            # Filter measurements with dimensions and metric name
            for d_key, d_value in dimensions.items():
                d_values = d_value.split("|") if d_value else None

                new_metrics = {}
                for metric_hash, metric in metrics.items():
                    if d_key not in metric.map:
                        break
                    if d_values is None or metric.map[d_key] in d_values:
                        new_metrics[metric_hash] = metric
                metrics = new_metrics

        # Get measurements
        measurements = self._get_measurements(tenant_id, region, metrics,
                                              start_timestamp=start_timestamp,
                                              end_timestamp=end_timestamp)

        requested_statistics = [stat.lower() for stat in statistics]

        if len(measurements) == 0:
            return []

        # Handle group-by
        measurements_per_groups = {}
        if group_by:
            for m in measurements:
                metric_map = metrics[m.metric_hash].map
                groups = tuple([metric_map.get(g) for g in group_by])
                if None in groups:
                    return []
                measurements_per_groups.setdefault(groups, [])
                measurements_per_groups[groups].append(m)
        else:
            measurements_per_groups[tuple()] = measurements

        # Check whether multiple metrics are in
        for groups, measurements in measurements_per_groups.items():
            metric_hashes = set([m.metric_hash for m in measurements])
            if len(metric_hashes) > 1 and not merge_metrics_flag:
                raise exceptions.MultipleMetricsException(
                    self.MULTIPLE_METRICS_MESSAGE)

        # Aggregate them and prepare the result
        result = []
        for groups, measurements in measurements_per_groups.items():
            columns = [u'timestamp']
            if 'avg' in requested_statistics:
                columns.append(u'avg')
            if 'min' in requested_statistics:
                columns.append(u'min')
            if 'max' in requested_statistics:
                columns.append(u'max')
            if 'count' in requested_statistics:
                columns.append(u'count')
            if 'sum' in requested_statistics:
                columns.append(u'sum')

            stats_list = []
            m = measurements[0]
            stats_count = stats_sum = 0
            stats_min = stats_max = m.value
            start_time = from_timestamp_ms(m.timestamp)
            milestone_timestamp_ms = (start_timestamp + period) * 1000
            period_ms = period * 1000

            def add_stat():
                if stats_count == 0:
                    return
                stat = [start_time]
                if 'avg' in requested_statistics:
                    stat.append(stats_sum / stats_count)
                if 'min' in requested_statistics:
                    stat.append(stats_min)
                if 'max' in requested_statistics:
                    stat.append(stats_max)
                if 'count' in requested_statistics:
                    stat.append(stats_count)
                if 'sum' in requested_statistics:
                    stat.append(stats_sum)
                stats_list.append(stat)

            for m in measurements:

                if m.timestamp > milestone_timestamp_ms:
                    add_stat()
                    stats_count = stats_sum = 0
                    stats_min = stats_max = m.value
                    start_time = from_timestamp_ms(m.timestamp)
                    # Akira: If polling period is a day and "period" is 300,
                    # using while loop like below takes 288 loops per measurement.
                    # while m.timestamp > milestone_timestamp_ms:
                    #     milestone_timestamp_ms += period * 1000
                    skip = int((m.timestamp - milestone_timestamp_ms) / period_ms)
                    milestone_timestamp_ms += period_ms * (skip + 1)

                stats_count += 1
                stats_sum += m.value
                if 'min' in requested_statistics and m.value < stats_min:
                    stats_min = m.value
                if 'max' in requested_statistics and m.value > stats_max:
                    stats_max = m.value

            add_stat()

            # Filter with limit
            if limit is not None:
                stats_list = stats_list[:limit]

            # Check whether stats list has no entry
            if len(stats_list) == 0:
                continue

            # Handle group-by
            if groups:
                dimensions = {key: value
                              for key, value in zip(group_by, groups)}

            result.append({
                u'name': name,
                u'id': stats_list[-1][0],
                u'dimensions': dimensions,
                u'columns': columns,
                u'statistics': stats_list
            })

        # Put the result
        return result

    @exception_handler
    def alarm_history(self, tenant_id, alarm_id_list,
                      offset, limit, start_timestamp=None,
                      end_timestamp=None):
        """Get alarm histories list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param alarm_id_list: List of alarm IDs
        :type alarm_id_list: list(str)
        :param offset: ID of the starting record
        :type offset: str or None
        :param limit: Max number of records
        :type limit: int or None
        :keyword start_timestamp: Starting timestamp in seconds
        :type start_timestamp: int
        :keyword end_timestamp: Ending timestamp in seconds
        :type end_timestamp: int
        :return: Metrics list
        :rtype: list(dict)
        """
        # Get alarm histories list
        alarm_histories = self._get_alarm_histories(
            tenant_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp)

        # Filter with alarm_id_list
        alarm_histories = [ah for ah in alarm_histories
                           if ah.alarm_id in alarm_id_list]

        # Filter with offset
        if offset is not None:
            offset = float(offset)
            ids = [ah.id for ah in alarm_histories]
            if offset not in ids:
                return []
            index = ids.index(offset)
            alarm_histories = alarm_histories[index:]

        # Filter with limit
        if limit is not None:
            alarm_histories = alarm_histories[:limit]

        alarm_histories_list = []
        for ah in alarm_histories:
            alarm = {u'timestamp': from_timestamp_ms(ah.timestamp),
                     u'alarm_id': ah.alarm_id,
                     u'metrics': ah.metrics,
                     u'new_state': ah.new_state,
                     u'old_state': ah.old_state,
                     u'reason': ah.reason,
                     u'reason_data': u'{}',
                     u'sub_alarms': ah.sub_alarms,
                     u'id': str(ah.id)}

            if ah.sub_alarms:
                for sub_alarm in ah.sub_alarms:
                    sub_expr = sub_alarm.get('sub_alarm_expression', {})
                    metric_def = sub_expr.get('metric_definition', {})
                    sub_expr['metric_name'] = metric_def.get('name', u'')
                    sub_expr['dimensions'] = metric_def.get('dimensions', {})
                    sub_expr.pop('metric_definition', None)

            alarm_histories_list.append(alarm)

        return alarm_histories_list

    @staticmethod
    def check_status():
        """Check the GridDB server is alive.

        :return: Health check result
        :rtype: (bool, str)
        """
        try:
            factory = griddb.StoreFactory.get_default()
            factory.get_store({
                "notificationAddress": CONF.griddb.notification_address,
                "notificationPort": str(CONF.griddb.notification_port),
                "clusterName": CONF.griddb.cluster_name,
                "user": CONF.griddb.user,
                "password": CONF.griddb.password
            })
        except griddb.GSException as ex:
            LOG.exception(str(ex.what()))
            return False, str(ex.what())
        return True, 'OK'
