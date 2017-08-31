# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP
# (C) Copyright 2017 SUSE LLC
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
from collections import namedtuple
from datetime import datetime
from datetime import timedelta
import itertools
import urllib

from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement

from oslo_config import cfg
from oslo_log import log

from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories import metrics_repository
from monasca_common.rest import utils as rest_utils

LOG = log.getLogger(__name__)

LIMIT_CLAUSE = 'limit %s'
ALLOW_FILTERING = 'allow filtering'

MEASUREMENT_LIST_CQL = ('select time_stamp, value, value_meta '
                        'from measurements where %s %s %s %s')
METRIC_ID_EQ = 'metric_id = %s'
METRIC_ID_IN = 'metric_id in %s'
OFFSET_TIME_GT = "and time_stamp > %s"
START_TIME_GE = "and time_stamp >= %s"
END_TIME_LE = "and time_stamp <= %s"

METRIC_LIST_CQL = ('select metric_name, dimensions, metric_id '
                   'from metrics where %s %s %s %s %s %s %s %s %s %s')
REGION_EQ = 'region = %s'
TENANT_EQ = 'and tenant_id = %s'
METRIC_NAME_EQ = 'and metric_name = %s'
DIMENSIONS_CONTAINS = 'and dimensions contains %s '
DIMENSIONS_NAME_CONTAINS = 'and dimension_names contains %s '
CREATED_TIME_LE = "and created_at <= %s"
UPDATED_TIME_GE = "and updated_at >= %s"
DIMENSIONS_GT = 'and dimensions > %s'

DIMENSION_VALUE_BY_METRIC_CQL = ('select dimension_value as value from metrics_dimensions '
                                 'where region = ? and tenant_id = ? and metric_name = ? '
                                 'and dimension_name = ? group by dimension_value')

DIMENSION_VALUE_CQL = ('select value from dimensions '
                       'where region = ? and tenant_id = ? and name = ? '
                       'group by value order by value')

DIMENSION_NAME_BY_METRIC_CQL = ('select dimension_name as name from metrics_dimensions where '
                                'region = ? and tenant_id = ? and metric_name = ? '
                                'group by dimension_name order by dimension_name')

DIMENSION_NAME_CQL = ('select name from dimensions where region = ? and tenant_id = ? '
                      'group by name allow filtering')

METRIC_NAME_BY_DIMENSION_CQL = ('select metric_name from dimensions_metrics where region = ? and '
                                'tenant_id = ? and dimension_name = ? and dimension_value = ? '
                                'group by metric_name order by metric_name')

METRIC_NAME_BY_DIMENSION_OFFSET_CQL = ('select metric_name from dimensions_metrics where region = ? and '
                                       'tenant_id = ? and dimension_name = ? and dimension_value = ? and '
                                       'metric_name >= ?'
                                       'group by metric_name order by metric_name')

METRIC_NAME_CQL = ('select distinct region, tenant_id, metric_name from metrics_dimensions '
                   'where region = ? and tenant_id = ? allow filtering')

METRIC_NAME_OFFSET_CQL = ('select distinct region, tenant_id, metric_name from metrics_dimensions '
                          'where region = ? and tenant_id = ? and metric_name >= ? allow filtering')

METRIC_BY_ID_CQL = ('select region, tenant_id, metric_name, dimensions from measurements '
                    'where metric_id = ? limit 1')

Metric = namedtuple('metric', 'id name dimensions')


class MetricsRepository(metrics_repository.AbstractMetricsRepository):
    def __init__(self):

        try:
            self.conf = cfg.CONF
            self.cluster = Cluster(self.conf.cassandra.contact_points)
            self.session = self.cluster.connect(self.conf.cassandra.keyspace)

            self.dim_val_by_metric_stmt = self.session.prepare(DIMENSION_VALUE_BY_METRIC_CQL)

            self.dim_val_stmt = self.session.prepare(DIMENSION_VALUE_CQL)

            self.dim_name_by_metric_stmt = self.session.prepare(DIMENSION_NAME_BY_METRIC_CQL)

            self.dim_name_stmt = self.session.prepare(DIMENSION_NAME_CQL)

            self.metric_name_by_dimension_stmt = self.session.prepare(METRIC_NAME_BY_DIMENSION_CQL)

            self.metric_name_by_dimension_offset_stmt = self.session.prepare(METRIC_NAME_BY_DIMENSION_OFFSET_CQL)

            self.metric_name_stmt = self.session.prepare(METRIC_NAME_CQL)

            self.metric_name_offset_stmt = self.session.prepare(METRIC_NAME_OFFSET_CQL)

            self.metric_by_id_stmt = self.session.prepare(METRIC_BY_ID_CQL)

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def list_dimension_values(self, tenant_id, region, metric_name,
                              dimension_name):

        try:
            if metric_name:
                rows = self.session.execute(
                    self.dim_val_by_metric_stmt,
                    [region, tenant_id, metric_name, dimension_name])
            else:
                rows = self.session.execute(
                    self.dim_val_stmt,
                    [region, tenant_id, dimension_name])

            json_dim_value_list = []

            if not rows:
                return json_dim_value_list

            for row in rows:
                json_dim_value_list.append({u'dimension_value': row.value})

            json_dim_value_list.sort(key=lambda x: x[u'dimension_value'])

            return json_dim_value_list
        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def list_dimension_names(self, tenant_id, region, metric_name):

        try:
            if metric_name:
                rows = self.session.execute(
                    self.dim_name_by_metric_stmt,
                    [region, tenant_id, metric_name])
                ordered = True
            else:
                rows = self.session.execute(
                    self.dim_name_stmt,
                    [region, tenant_id])
                ordered = False

            if not rows:
                return []

            json_dim_name_list = [{u'dimension_name': row.name} for row in rows]

            if not ordered:
                json_dim_name_list.sort(key=lambda x: x[u'dimension_name'])

            return json_dim_name_list
        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def list_metrics(self, tenant_id, region, name, dimensions, offset, limit, start_time=None,
                     end_time=None):
        try:
            offset_name = None
            offset_dimensions = []
            if offset:
                offset_metric = self._get_metric_by_id(offset)
                if offset_metric:
                    offset_name = offset_metric.name
                    offset_dimensions = offset_metric.dimensions

            names = []
            if not name:
                names = self._list_metric_names(tenant_id, region, dimensions, offset=offset_name)
                if names:
                    names = [elem['name'] for elem in names]
            else:
                names.append(name)

            metric_list = []
            offset_futures = []
            non_offset_futures = []

            if not names:
                return metric_list

            for name in names:
                if name == offset_name:
                    if offset_dimensions and dimensions:
                        offset_futures.extend(
                            self._list_metrics_by_name(tenant_id, region, name, dimensions, offset_dimensions, limit,
                                                       start_time=None, end_time=None))
                    else:
                        non_offset_futures.extend(
                            self._list_metrics_by_name(tenant_id, region, name, dimensions, offset_dimensions, limit,
                                                       start_time=None, end_time=None))
                else:
                    non_offset_futures.extend(
                        self._list_metrics_by_name(tenant_id, region, name, dimensions, None, limit,
                                                   start_time=None, end_time=None))

            # manually filter out metrics by the offset dimension
            for future in offset_futures:
                rows = future.result()
                for row in rows:
                    if offset_dimensions >= row.dimensions:
                        continue

                    metric_list.append(self._process_metric_row(row))

            for future in non_offset_futures:
                rows = future.result()
                for row in rows:
                    metric_list.append(self._process_metric_row(row))

            return metric_list

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def _process_metric_row(self, row):
        dim_map = {}
        for d in row.dimensions:
            pair = d.split('\t')
            dim_map[pair[0]] = pair[1]

        metric = {}
        metric['id'] = binascii.hexlify(bytearray(row.metric_id))
        metric['name'] = row.metric_name
        metric['dimensions'] = dim_map

        return metric

    def _list_metrics_by_name(self, tenant_id, region, name, dimensions, dimension_offset, limit, start_time=None,
                              end_time=None):

        or_dimensions = []
        sub_dimensions = {}
        futures = []

        if dimensions:
            wildcard_dimensions = []
            for key, value in dimensions.items():
                if not value:
                    wildcard_dimensions.append(key)

                elif '|' in value:

                    def f(val):
                        return {key: val}

                    or_dimensions.append(list(map(f, sorted(value.split('|')))))

                else:
                    sub_dimensions[key] = value

            if or_dimensions:
                or_dims_list = list(itertools.product(*or_dimensions))

                for or_dims_tuple in or_dims_list:
                    extracted_dimensions = sub_dimensions.copy()

                    for dims in iter(or_dims_tuple):
                        for k, v in dims.iteritems():
                            extracted_dimensions[k] = v

                    query = self._build_metrics_by_name_query(tenant_id, region, name, extracted_dimensions,
                                                              wildcard_dimensions, start_time,
                                                              end_time, dimension_offset, limit)

                    futures.append(self.session.execute_async(query[0], query[1]))

            else:
                query = self._build_metrics_by_name_query(tenant_id, region, name, sub_dimensions, wildcard_dimensions,
                                                          start_time,
                                                          end_time, dimension_offset, limit)
                futures.append(self.session.execute_async(query[0], query[1]))

        else:
            query = self._build_metrics_by_name_query(tenant_id, region, name, dimensions, None, start_time,
                                                      end_time, dimension_offset, limit)
            futures.append(self.session.execute_async(query[0], query[1]))

        return futures

    def _get_metric_by_id(self, metric_id):

        rows = self.session.execute(self.metric_by_id_stmt, [bytearray.fromhex(metric_id)])

        if rows:
            return Metric(id=metric_id, name=rows[0].metric_name, dimensions=rows[0].dimensions)

        return None

    def _build_metrics_by_name_query(self, tenant_id, region, name, dimensions, wildcard_dimensions, start_time,
                                     end_time, dim_offset,
                                     limit):

        conditions = [REGION_EQ, TENANT_EQ]
        params = [region, tenant_id.encode('utf8')]

        if name:
            conditions.append(METRIC_NAME_EQ)
            params.append(name)
        else:
            conditions.append('')

        if dimensions:
            conditions.append(DIMENSIONS_CONTAINS * len(dimensions))
            params.extend(
                [self._create_dimension_value_entry(dim_name, dim_value)
                 for dim_name, dim_value in dimensions.items()])
        else:
            conditions.append('')

        if wildcard_dimensions:
            conditions.append(DIMENSIONS_NAME_CONTAINS * len(wildcard_dimensions))
            params.extend(wildcard_dimensions)
        else:
            conditions.append('')

        if dim_offset and not dimensions:
            # cassandra does not allow using both contains and GT in collection column
            conditions.append(DIMENSIONS_GT)
            params.append(dim_offset)
        else:
            conditions.append('')

        if start_time:
            conditions.append(UPDATED_TIME_GE % start_time)
        else:
            conditions.append('')

        if end_time:
            conditions.append(CREATED_TIME_LE % end_time)
        else:
            conditions.append('')

        if limit:
            conditions.append(LIMIT_CLAUSE)
            params.append(limit)
        else:
            conditions.append('')

        if (not name) or dimensions or wildcard_dimensions or start_time or end_time:
            conditions.append(ALLOW_FILTERING)
        else:
            conditions.append('')

        return METRIC_LIST_CQL % tuple(conditions), params

    def _create_dimension_value_entry(self, name, value):
        return '%s\t%s' % (name, value)

    def list_metric_names(self, tenant_id, region, dimensions):
        return self._list_metric_names(tenant_id, region, dimensions)

    def _list_metric_names(self, tenant_id, region, dimensions, offset=None):

        or_dimensions = []
        single_dimensions = {}

        if dimensions:
            for key, value in dimensions.items():
                if not value:
                    continue

                elif '|' in value:
                    def f(val):
                        return {key: val}

                    or_dimensions.append(list(map(f, sorted(value.split('|')))))

                else:
                    single_dimensions[key] = value

        if or_dimensions:

            names = []
            or_dims_list = list(itertools.product(*or_dimensions))

            for or_dims_tuple in or_dims_list:
                extracted_dimensions = single_dimensions.copy()

                for dims in iter(or_dims_tuple):
                    for k, v in dims.iteritems():
                        extracted_dimensions[k] = v

                names.extend(
                    self._list_metric_names_single_dimension_value(tenant_id, region, extracted_dimensions, offset))

            names.sort(key=lambda x: x[u'name'])
            return names

        else:
            names = self._list_metric_names_single_dimension_value(tenant_id, region, single_dimensions, offset)
            names.sort(key=lambda x: x[u'name'])
            return names

    def _list_metric_names_single_dimension_value(self, tenant_id, region, dimensions, offset=None):

        try:
            futures = []
            if dimensions:
                for name, value in dimensions.items():
                    if offset:
                        futures.append(self.session.execute_async(self.metric_name_by_dimension_offset_stmt,
                                                                  [region, tenant_id, name, value, offset]))
                    else:
                        futures.append(self.session.execute_async(self.metric_name_by_dimension_stmt,
                                                                  [region, tenant_id, name, value]))

            else:
                if offset:
                    futures.append(
                        self.session.execute_async(self.metric_name_offset_stmt, [region, tenant_id, offset]))
                else:
                    futures.append(self.session.execute_async(self.metric_name_stmt, [region, tenant_id]))

            names_list = []

            for future in futures:
                rows = future.result()
                tmp = set()
                for row in rows:
                    tmp.add(row.metric_name)

                names_list.append(tmp)

            return [{u'name': v} for v in set.intersection(*names_list)]

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def measurement_list(self, tenant_id, region, name, dimensions,
                         start_timestamp, end_timestamp, offset, limit,
                         merge_metrics_flag, group_by):

        metrics = self.list_metrics(tenant_id, region, name, dimensions, None, None)

        if offset:
            tmp = offset.split("_")
            if len(tmp) > 1:
                offset_id = tmp[0]
                offset_timestamp = tmp[1]
            else:
                offset_id = None
                offset_timestamp = offset
        else:
            offset_timestamp = None
            offset_id = None

        if not metrics:
            return None
        elif len(metrics) > 1:
            if not merge_metrics_flag and not group_by:
                raise exceptions.MultipleMetricsException(self.MULTIPLE_METRICS_MESSAGE)

        try:
            if len(metrics) > 1 and not group_by:
                # ignore offset_id even it is set
                count, series_list = self._query_merge_measurements(metrics,
                                                                    dimensions,
                                                                    start_timestamp,
                                                                    end_timestamp,
                                                                    offset_timestamp,
                                                                    limit)
                return series_list

            if group_by is not None and not isinstance(group_by, list):
                group_by = str(group_by).split(',')

            if len(metrics) == 1 or group_by[0].startswith('*'):
                if offset_id:
                    for index, metric in enumerate(metrics):
                        if metric['id'] == offset_id:
                            if index > 0:
                                metrics[0:index] = []
                            break

                count, series_list = self._query_measurements(metrics,
                                                              start_timestamp,
                                                              end_timestamp,
                                                              offset_timestamp,
                                                              limit)

                return series_list

            grouped_metrics = self._group_metrics(metrics, group_by, dimensions)

            if offset_id:
                found_offset = False
                for outer_index, sublist in enumerate(grouped_metrics):
                    for inner_index, metric in enumerate(sublist):
                        if metric['id'] == offset_id:
                            found_offset = True
                            if inner_index > 0:
                                sublist[0:inner_index] = []
                            break
                    if found_offset:
                        if outer_index > 0:
                            grouped_metrics[0:outer_index] = []
                        break

            series_list = []
            count = 0
            for index, sublist in enumerate(grouped_metrics):
                if index == 0:
                    sub_count, results = self._query_merge_measurements(sublist,
                                                                        sublist[0]['dimensions'],
                                                                        start_timestamp,
                                                                        end_timestamp,
                                                                        offset_timestamp,
                                                                        limit)
                else:
                    sub_count, results = self._query_merge_measurements(sublist,
                                                                        sublist[0]['dimensions'],
                                                                        start_timestamp,
                                                                        end_timestamp,
                                                                        None,
                                                                        limit - count)

                count += sub_count

                series_list.extend(results)

                if count >= limit:
                    break

            return series_list

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def _query_merge_measurements(self, metrics, dimensions, start_timestamp, end_timestamp,
                                  offset_timestamp, limit):
        results = []
        for metric in metrics:
            if limit:
                fetch_size = min(limit, max(1000, limit / len(metrics)))
            else:
                fetch_size = None
            query = self._build_measurement_query(metric['id'],
                                                  start_timestamp,
                                                  end_timestamp,
                                                  offset_timestamp,
                                                  limit,
                                                  fetch_size)
            results.append((metric, iter(self.session.execute_async(query[0], query[1]).result())))

        return self._merge_series(results, dimensions, limit)

    def _query_measurements(self, metrics, start_timestamp, end_timestamp,
                            offset_timestamp, limit):
        results = []
        for index, metric in enumerate(metrics):
            if index == 0:
                query = self._build_measurement_query(metric['id'],
                                                      start_timestamp,
                                                      end_timestamp,
                                                      offset_timestamp,
                                                      limit)
            else:
                if limit:
                    fetech_size = min(5000, max(1000, limit / min(index, 4)))
                query = self._build_measurement_query(metric['id'],
                                                      start_timestamp,
                                                      end_timestamp,
                                                      None,
                                                      limit,
                                                      fetech_size)

            results.append([metric,
                            iter(self.session.execute_async(query[0], query[1]).result())])

        series_list = []
        count = 0
        for result in results:
            measurements = []
            row = next(result[1], None)
            while row:
                measurements.append([self._isotime_msec(row.time_stamp),
                                     row.value,
                                     rest_utils.from_json(row.value_meta) if row.value_meta else {}])
                count += 1
                if count >= limit:
                    break

                row = next(result[1], None)

            series_list.append({'name': result[0]['name'],
                                'id': result[0]['id'],
                                'columns': ['timestamp', 'value', 'value_meta'],
                                'measurements': measurements,
                                'dimensions': result[0]['dimensions']})
            if count >= limit:
                break

        return count, series_list

    def _build_measurement_query(self, metric_id, start_timestamp,
                                 end_timestamp, offset_timestamp,
                                 limit=None, fetch_size=None):
        conditions = [METRIC_ID_EQ]
        params = [bytearray.fromhex(metric_id)]

        if offset_timestamp:
            conditions.append(OFFSET_TIME_GT)
            params.append(offset_timestamp)
        elif start_timestamp:
            conditions.append(START_TIME_GE)
            params.append(int(start_timestamp * 1000))
        else:
            conditions.append('')

        if end_timestamp:
            conditions.append(END_TIME_LE)
            params.append(int(end_timestamp * 1000))
        else:
            conditions.append('')

        if limit:
            conditions.append(LIMIT_CLAUSE)
            params.append(limit)
        else:
            conditions.append('')

        return SimpleStatement(MEASUREMENT_LIST_CQL % tuple(conditions), fetch_size=fetch_size), params

    def _merge_series(self, series, dimensions, limit):
        series_list = []

        if not series:
            return series_list

        measurements = []
        top_batch = []
        num_series = len(series)
        for i in range(0, num_series):
            row = next(series[i][1], None)
            if row:
                top_batch.append([i,
                                  row.time_stamp,
                                  row.value,
                                  rest_utils.from_json(row.value_meta) if row.value_meta else {}])
            else:
                num_series -= 1

        top_batch.sort(key=lambda m: m[1], reverse=True)

        count = 0
        while count < limit and top_batch:
            measurements.append([self._isotime_msec(top_batch[num_series - 1][1]),
                                 top_batch[num_series - 1][2],
                                 top_batch[num_series - 1][3]])
            count += 1
            row = next(series[top_batch[num_series - 1][0]][1], None)
            if row:
                top_batch[num_series - 1] = [top_batch[num_series - 1][0],
                                             row.time_stamp,
                                             row.value,
                                             rest_utils.from_json(row.value_meta) if row.value_meta else {}]

                top_batch.sort(key=lambda m: m[1], reverse=True)
            else:
                num_series -= 1
                top_batch.pop()

        series_list.append({'name': series[0][0]['name'],
                            'id': series[0][0]['id'],
                            'columns': ['timestamp', 'value', 'value_meta'],
                            'measurements': measurements,
                            'dimensions': dimensions})

        return count, series_list

    @staticmethod
    def _group_metrics(metrics, group_by, search_by):
        grouped_metrics = {}
        for metric in metrics:
            key = ''
            display_dimensions = dict(search_by.items())
            for name in group_by:
                # '_' ensures te key with missing dimension is sorted lower
                value = metric['dimensions'].get(name, '_')
                if value != '_':
                    display_dimensions[name] = value
                key = key + '='.join((urllib.quote_plus(name), urllib.quote_plus(value))) + '&'

            if key in grouped_metrics:
                grouped_metrics[key].append(metric)
            else:
                grouped_metrics[key] = [metric]

            metric['dimensions'] = display_dimensions

        grouped_metrics = grouped_metrics.items()
        grouped_metrics.sort(key=lambda x: x[0])
        return [x[1] for x in grouped_metrics]

    @staticmethod
    def _isotime_msec(timestamp):
        """Stringify datetime in ISO 8601 format + millisecond.
        """
        st = timestamp.isoformat()
        if '.' in st:
            st = st[:23] + 'Z'
        else:
            st += '.000Z'
        return st.decode('utf8')

    def metrics_statistics(self, tenant_id, region, name, dimensions,
                           start_timestamp, end_timestamp, statistics,
                           period, offset, limit, merge_metrics_flag,
                           group_by):
        try:

            if not period:
                period = 300
            period = int(period)

            # calculates stats. could implement as UDA when single metric, if deemed to be necessary.
            series_list = self.measurement_list(tenant_id, region, name, dimensions,
                                                start_timestamp, end_timestamp,
                                                offset, limit, merge_metrics_flag, group_by)

            json_statistics_list = []

            if not series_list:
                return json_statistics_list

            requested_statistics = [stat.lower() for stat in statistics]

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

            for series in series_list:
                series['columns'] = columns
                measurements = series['measurements']

            first_measure = measurements[0]
            stats_count = 0
            stats_sum = 0
            stats_max = first_measure['value']
            stats_min = stats_max
            start_period = first_measure.time_stamp

            stats_list = []

            start_datetime = datetime.utcfromtimestamp(start_timestamp)
            if offset and offset > start_datetime:
                tmp_start_period = offset
            else:
                tmp_start_period = start_datetime

            while start_period >= tmp_start_period + timedelta(seconds=period):
                stat = [
                    tmp_start_period.strftime('%Y-%m-%dT%H:%M:%SZ').decode('utf8')
                ]
                for _statistics in requested_statistics:
                    stat.append(0)
                tmp_start_period += timedelta(seconds=period)
                stats_list.append(stat)

            for measurement in series['measurements']:

                time_stamp = measurement['time_stamp']
                value = measurement['value']

                if (time_stamp - start_period).seconds >= period:

                    stat = [
                        start_period.strftime('%Y-%m-%dT%H:%M:%SZ').decode(
                            'utf8')]

                    if 'avg' in requested_statistics:
                        stat.append(stats_sum / stats_count)

                    if 'min' in requested_statistics:
                        stat.append(stats_min)

                        stats_min = value

                    if 'max' in requested_statistics:
                        stat.append(stats_max)

                        stats_max = value

                    if 'count' in requested_statistics:
                        stat.append(stats_count)

                    if 'sum' in requested_statistics:
                        stat.append(stats_sum)

                    stats_list.append(stat)

                    tmp_start_period = start_period + timedelta(seconds=period)
                    while time_stamp > tmp_start_period:
                        stat = [
                            tmp_start_period.strftime('%Y-%m-%dT%H:%M:%SZ').decode('utf8')
                        ]
                        for _statistics in requested_statistics:
                            stat.append(0)
                        tmp_start_period += timedelta(seconds=period)
                        stats_list.append(stat)

                    start_period = time_stamp

                    stats_sum = 0
                    stats_count = 0

                stats_count += 1
                stats_sum += value

                if 'min' in requested_statistics:

                    if value < stats_min:
                        stats_min = value

                if 'max' in requested_statistics:

                    if value > stats_max:
                        stats_max = value

            if stats_count:

                stat = [start_period.strftime('%Y-%m-%dT%H:%M:%SZ').decode('utf8')]

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

                if end_timestamp:
                    time_stamp = datetime.utcfromtimestamp(end_timestamp)
                else:
                    time_stamp = datetime.now()
                tmp_start_period = start_period + timedelta(seconds=period)
                while time_stamp > tmp_start_period:
                    stat = [
                        tmp_start_period.strftime('%Y-%m-%dT%H:%M:%SZ').decode('utf8')
                    ]
                    for _statistics in requested_statistics:
                        stat.append(0)
                    tmp_start_period += timedelta(seconds=period)
                    stats_list.append(stat)

            statistic = {u'name': name.decode('utf8'),
                         # The last date in the stats list.
                         u'id': stats_list[-1][0],
                         u'dimensions': dimensions,
                         u'columns': columns,
                         u'statistics': stats_list}

            json_statistics_list.append(statistic)

            return json_statistics_list

        except exceptions.RepositoryException as ex:
            LOG.exception(ex)
            raise ex

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

        return []

    def alarm_history(self, tenant_id, alarm_id_list, offset, limit,
                      start_timestamp, end_timestamp):
        return []
