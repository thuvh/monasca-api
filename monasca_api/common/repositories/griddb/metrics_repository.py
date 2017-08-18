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

import binascii
from datetime import datetime
import string
import urllib

import griddb_python_client as griddb

from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories import metrics_repository

from monasca_common.rest.utils import from_json

from oslo_config import cfg

from oslo_log import log

from oslo_utils import timeutils

LOG = log.getLogger(__name__)

TIME_SERIES_CHARACTERS = string.digits + string.ascii_letters

MEASUREMENT_PREFIX = "mon_measure"
ALARM_STATE_HISTORY_PREFIX = "mon_ash"


def from_timestamp(timestamp):
    """Stringify datetime in ISO 8601 format + millisecond.

    :param timestamp: Timestamp with milliseconds
    :type timestamp: int
    :return: ISO 8601-style date time
    :rtype: str
    """
    st = datetime.utcfromtimestamp(float(timestamp) / 1000).isoformat()
    if '.' in st:
        st = st[:23] + 'Z'
    else:
        st += '.000Z'
    return st.decode('utf8')


def to_timestamp(date_time_string):
    """Make timestamp from ISO 8601 format.

    :param date_time_string: ISO 8601-style date time
    :type date_time_string: str
    :return: Timestamp in milliseconds
    :rtype: int
    """
    dt = timeutils.parse_isotime(date_time_string)
    dt = timeutils.normalize_time(dt)
    timestamp = (dt - datetime.datetime(1970, 1, 1)).total_seconds()
    return timestamp * 1000


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
        self.conf = cfg.CONF
        self.factory = griddb.StoreFactory.get_default()
        self.gridstore = self.factory.get_store({
            "notificationAddress": self.conf.griddb.notification_address,
            "notificationPort": str(self.conf.griddb.notification_port),
            "clusterName": self.conf.griddb.cluster_name,
            "user": self.conf.griddb.user,
            "password": self.conf.griddb.password
        })

    @gsexception_handler
    def _get_time_series(self, *args):
        """Aquire time series object of GridDB.

        :param args: tuple for the time series name
        :type args: list(str)
        :return: time series object
        :rtype: griddb.Container
        """
        ts_name = "".join([_ for _ in "".join(args)
                           if _ in TIME_SERIES_CHARACTERS]) + "01"
        return self.gridstore.get_container(ts_name)

    @gsexception_handler
    def _get_metrics(self, tenant_id, region,
                     start_timestamp=None, end_timestamp=None):
        """Get metrics in a measurement container.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :keyword start_timestamp: Starting timestamp in milliseconds
        :type start_timestamp: int
        :keyword end_timestamp: Ending timestamp in milliseconds
        :type end_timestamp: int
        :return: Metrics list
        :rtype: list(tuple)
        """
        # Query measurement records
        ts = self._get_time_series(MEASUREMENT_PREFIX, region, tenant_id)
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
        metrics = {}
        while rs.has_next():
            rs.get_next(row)
            metric_hash = urllib.quote(str(row.get_field_as_blob(1)))
            metric_map = from_json(row.get_field_as_string(2))
            metrics[metric_hash] = metric_map

        return sorted(metrics.items())

    @gsexception_handler
    def _get_measurements(self, tenant_id, region,
                         start_timestamp=None, end_timestamp=None):
        """Get measurement in a measurement container.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :keyword start_timestamp: Starting timestamp in milliseconds
        :type start_timestamp: int
        :keyword end_timestamp: Ending timestamp in milliseconds
        :type end_timestamp: int
        :return: Measurement list
        :rtype: list(tuple)
        """
        # Query measurement records
        ts = self._get_time_series(MEASUREMENT_PREFIX, region, tenant_id)
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
        LOG.debug("query: %s", query_string)
        query = ts.query(query_string)

        # Fetch query results
        rs = query.fetch(False)
        row = ts.create_row()

        # Store them into a list
        measurements = []
        while rs.has_next():
            rs.get_next(row)
            measurements.append((
                row.get_field_as_timestamp(0),  # timestamp
                urllib.quote(str(row.get_field_as_blob(1))),  # hash
                from_json(row.get_field_as_string(2)),  # map
                row.get_field_as_float(3),  # value
                from_json(row.get_field_as_string(4))  # value_map
            ))

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
        :return: Alarm history list
        :rtype: list(tuple)
        """
        # Query alarm hisotry records
        ts = self._get_time_series(ALARM_STATE_HISTORY_PREFIX, tenant_id)
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
        alarm_state_histories = []
        while rs.has_next():
            rs.get_next(row)
            alarm_state_histories.append((
                row.get_field_as_timestamp(0),  # timestamp
                row.get_field_as_string(1),  # alarm_id
                from_json(row.get_field_as_string(2)),  # metrics
                row.get_field_as_string(3),  # new_state
                row.get_field_as_string(4),  # old_state
                row.get_field_as_string(5),  # reason
                from_json(row.get_field_as_string(6)),  # sub_alarms
                row.get_field_as_float(7)  # id
            ))

        return alarm_state_histories

    @exception_handler
    def list_metrics(self, tenant_id, region, name, dimensions, offset,
                     limit, start_timestamp=None, end_timestamp=None,
                     include_metric_hash=False):
        """Aquire metrics list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :param dimensions: Searching conditions
        :type dimensions: dict
        :param offset: ID of the starting record
        :type offset: str
        :param limit: Max number of records
        :type limit: int
        :keyword start_timestamp: Starting timestamp in milliseconds
        :type start_timestamp: int
        :keyword end_timestamp: Ending timestamp in milliseconds
        :type end_timestamp: int
        :return: Metrics list
        :rtype: list(dict)
        """
        # Get metrics
        metrics = self._get_metrics(tenant_id, region,
                                    start_timestamp=start_timestamp,
                                    end_timestamp=end_timestamp)

        # Add name to dimensions
        if name != "":
            dimensions["__name__"] = name

        # Filter metrics with dimensions and name
        if dimensions:
            for key, value in dimensions.items():
                if value == "":
                    values = None
                else:
                    values = value.split("|")

                new_metrics = []
                for metric_hash, metric_map in metrics:
                    if key not in metric_map:
                        break
                    if values is None or metric_map[key] in values:
                        new_metrics.append((metric_hash, metric_map))
                metrics = new_metrics

        # Filter metrics with offset
        metric_hashes = [_[0] for _ in metrics]
        if offset is not None:
            if offset not in metric_hashes:
                return []
            index = metric_hashes.index(offset)
            metrics = metrics[index:]

        # Limit record number of metrics
        if limit is not None:
            metrics = metrics[:limit]

        metrics_list = []
        for metric_hash, dimensions in metrics:
            name = dimensions.pop("__name__", None)
            metric_map = {
                "id": binascii.hexlify(metric_hash),
                "dimensions": dimensions
            }
            if name is not None:
                metric_map["name"] = name
            if include_metric_hash:
                metric_map["metric_hash"] = metric_hash
            metrics_list.append(metric_map)

        return metrics_list

    @exception_handler
    def list_metric_names(self, tenant_id, region, dimensions):
        """Aquire metric names list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :param dimensions: Searching conditions
        :type dimensions: dict
        :param offset: ID of the starting record
        :type offset: str
        :return: Metric names list
        :rtype: list(dict)
        """
        # Get metric list
        metrics = self._get_metrics(tenant_id, region)

        # Filter metrics with dimensions
        metric_names_list = set()
        for metric_hash, metric_map in metrics:
            name = metric_map.get('__name__')
            if name is not None:
                metric_names_list.add(name)

        return [{'name': _} for _ in metric_names_list]

    @exception_handler
    def list_dimension_names(self, tenant_id, region, metric_name):
        """Aquire dimension names list.

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
        metrics = self._get_metrics(tenant_id, region)

        # Filter metrics with metric_name
        dimension_names_list = set()
        for metric_hash, metric_map in metrics:
            name = metric_map.pop("__name__", None)
            if metric_name and metric_name != name:
                continue
            dimension_names_list.update(metric_map.keys())

        return [{'dimension_name': _} for _ in dimension_names_list]

    @exception_handler
    def list_dimension_values(self, tenant_id, region, metric_name,
                              dimension_name):
        """Aquire dimension values list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :param metric_name: Metric name
        :type metric_name: str or None
        :param dimensions: Searching conditions
        :type dimensions: dict
        :type end_timestamp: int
        :return: Metrics list
        :rtype: list(dict)
        """
        # Get metric list
        metrics = self._get_metrics(tenant_id, region)

        # Filter metrics with dimension_name
        dimension_values_list = set()
        for metric_hash, metric_map in metrics:
            if metric_name and metric_name != metric_map.get("__name__"):
                continue
            if dimension_name not in metric_map:
                continue
            dimension_values_list.add(metric_map[dimension_name])

        return [{'dimension_value': _} for _ in dimension_values_list]

    @exception_handler
    def measurement_list(self, tenant_id, region, name, dimensions,
                         start_timestamp, end_timestamp, offset,
                         limit, merge_metrics_flag, group_by):
        """Aquire measurement list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :param name: Metric name
        :type name: str
        :param dimensions: Searching conditions
        :type dimensions: dict
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
        :type group_by: str
        :return: Metrics list
        :rtype: list(dict)
        """
        if offset is not None:
            offset_timestamp = to_timestamp(offset)
            if offset_timestamp > start_timestamp:
                start_timestamp = offset_timestamp

        LOG.debug("start_timestamp: %s (%s)", start_timestamp, type(start_timestamp))

        # Get measurement list
        measurements = self._get_measurements(tenant_id, region,
                                              start_timestamp=start_timestamp,
                                              end_timestamp=end_timestamp)

        # Add metric name to dimensions
        if name != "":
            dimensions["__name__"] = name

        # Filter measurements with dimensions and metric name
        if dimensions:
            for key, value in dimensions.items():
                if value == "":
                    values = None
                else:
                    values = value.split("|")

                new_measurements = []
                for measurement in measurements:
                    metric_map = measurement[2]
                    if key not in metric_map:
                        break
                    if values is None or metric_map[key] in values:
                        new_measurements.append(measurement)
                measurements = new_measurements

        # Remove metric name from dimensions
        dimensions.pop("__name__", None)

        # Limit record number
        if limit is not None:
            measurements = measurements[:limit]

        # Check whether measurement list has no entry
        if len(measurements) == 0:
            return []

        # Check whether multiple metrics are in
        metric_hashes = set([_[1] for _ in measurements])
        if len(metric_hashes) > 1 and not merge_metrics_flag:
            raise exceptions.MultipleMetricsException(
                self.MULTIPLE_METRICS_MESSAGE)

        measurements_list = [
            (from_timestamp(timestamp), value, value_map)
            for timestamp, _hash, _map, value, value_map in measurements]

        return [{u'name': name,
                 u'id': measurements_list[-1][0],
                 u'dimensions': dimensions,
                 u'columns': [u'timestamp', u'value', u'value_meta'],
                 u'measurements': measurements_list}]

    @exception_handler
    def metrics_statistics(self, tenant_id, region, name, dimensions,
                           start_timestamp, end_timestamp, statistics,
                           period, offset, limit, merge_metrics_flag,
                           group_by):
        """Aquire measurement list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param region: Region name
        :type region: str
        :param name: Metric name
        :type name: str
        :param dimensions: Searching conditions
        :type dimensions: dict
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
        :type group_by: str
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

        measurements = self._get_measurements(tenant_id, region,
                                              start_timestamp=start_timestamp,
                                              end_timestamp=end_timestamp)

        requested_statistics = [stat.lower() for stat in statistics]

        # Add metric name to dimensions
        if name != "":
            dimensions["__name__"] = name

        # Filter measurements with dimensions and metric name
        if dimensions:
            for key, value in dimensions.items():
                if value == "":
                    values = None
                else:
                    values = value.split("|")

                new_measurements = []
                for measurement in measurements:
                    metric_map = measurement[2]
                    if key not in metric_map:
                        break
                    if values is None or metric_map[key] in values:
                        new_measurements.append(measurement)
                measurements = new_measurements

        # Remove metric name from dimensions
        dimensions.pop("__name__", None)

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
        timestamp, _hash, _map, value, value_map = measurements[0]
        stats_count = stats_sum = 0
        stats_min = stats_max = value
        start_time = from_timestamp(timestamp)
        milestone_timestamp = (start_timestamp + period) * 1000

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

        for timestamp, _hash, _map, value, value_map in measurements:

            if timestamp > milestone_timestamp:
                add_stat()
                stats_min = stats_max = value
                stats_count = stats_sum = 0
                start_time = from_timestamp(timestamp)
                milestone_timestamp += period * 1000

            stats_count += 1
            stats_sum += value
            if 'min' in requested_statistics and value < stats_min:
                stats_min = value
            if 'max' in requested_statistics and value > stats_max:
                stats_max = value

        add_stat()

        # Check whether stats list has no entry
        if len(stats_list) == 0:
            return []

        return [{u'name': name,
                 u'id': stats_list[-1][0],
                 u'dimensions': dimensions,
                 u'columns': columns,
                 u'statistics': stats_list}]

    @exception_handler
    def alarm_history(self, tenant_id, alarm_id_list,
                      offset, limit, start_timestamp=None,
                      end_timestamp=None):
        """Aquire alarm history list.

        :param tenant_id: Tenant ID
        :type tenant_id: str
        :param alarm_id_list: List of alarm IDs
        :type alarm_id_list: list(str)
        :param offset: ID of the starting record
        :type offset: str
        :param limit: Max number of records
        :type limit: int
        :keyword start_timestamp: Starting timestamp in milliseconds
        :type start_timestamp: int
        :keyword end_timestamp: Ending timestamp in milliseconds
        :type end_timestamp: int
        :return: Metrics list
        :rtype: list(dict)
        """
        # Get alarm history list
        alarm_histories = self._get_alarm_histories(
            tenant_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp)

        # Filter with alarm_id_list
        alarm_histories = [_ for _ in alarm_histories
                           if _[1] in alarm_id_list]

        # Filter with offset
        if offset is not None:
            offset = float(offset)
            ids = [_[7] for _ in alarm_histories]
            if offset not in ids:
                return []
            index = ids.index(offset)
            alarm_histories = alarm_histories[index:]

        # Filter with limit
        if limit is not None:
            alarm_histories = alarm_histories[:limit]

        alarm_histories_list = []
        for (timestamp, alarm_id, metrics, new_state, old_state, reason,
             reason_data, sub_alarms, _id) in alarm_histories:

            alarm = {u'timestamp': from_timestamp(timestamp),
                     u'alarm_id': alarm_id,
                     u'metrics': from_json(metrics),
                     u'new_state': new_state,
                     u'old_state': old_state,
                     u'reason': reason,
                     u'reason_data': u'{}',
                     u'sub_alarms': from_json(sub_alarms),
                     u'id': str(id)}

            if alarm[u'sub_alarms']:
                for sub_alarm in alarm[u'sub_alarms']:
                    sub_expr = sub_alarm['sub_alarm_expression']
                    metric_def = sub_expr['metric_definition']
                    sub_expr['metric_name'] = metric_def['name']
                    sub_expr['dimensions'] = metric_def['dimensions']
                    del sub_expr['metric_definition']

            alarm_histories_list.append(alarm)

        return alarm_histories_list
