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
                   'from metrics where %s %s %s %s %s %s %s')
REGION_EQ = 'region = %s'
TENANT_EQ = 'and tenant_id = %s'
METRIC_NAME_EQ = 'and metric_name = %s'
DIMENSION_CONTAINS = 'and dimensions contains %s'
OFFSET_ID_GT = 'and metric_id > %s'

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

METRIC_NAME_CQL = ('select distinct region, tenant_id, metric_name from metrics_dimensions '
                   'where region = ? and tenant_id = ? allow filtering')


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

            self.metric_name_stmt = self.session.prepare(METRIC_NAME_CQL)

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
                orderedList = True
            else:
                rows = self.session.execute(
                    self.dim_name_stmt,
                    [region, tenant_id])
                orderedList = False

            if not rows:
                return []

            json_dim_name_list = [{u'dimension_name': row.name} for row in rows]

            if not orderedList:
                json_dim_name_list.sort(key=lambda x: x[u'dimension_name'])

            return json_dim_name_list
        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def list_metrics(self, tenant_id, region, name, dimensions, offset,
                     limit, start_timestamp=None, end_timestamp=None):

        metric_list = self._list_metrics(tenant_id, region, name, dimensions, offset,
                                         limit)

        if start_timestamp or end_timestamp:
            final_list = []
            for metric in metric_list:
                series_list = self._measurement_list(metric, dimensions, start_timestamp, end_timestamp, None,
                                                     1, None, None)
                if series_list and len(series_list[0]['measurments']) > 0:
                    final_list.append(metric)

            return final_list

        return metric_list

    def _list_metrics(self, tenant_id, region, name, dimensions, offset, limit):

        or_dimensions = []
        sub_dimensions = {}
        futures = []

        if dimensions:
            for key, value in dimensions.items():
                if not value:
                    # does not support search by key only
                    LOG.info('Ignored search by dimension key only in dimension dictionary: %s' % dimensions)

                elif '|' in value:
                    def f(val):
                        return {key: val}

                    or_dimensions.append(list(map(f, value.split('|'))))

                else:
                    sub_dimensions[key] = value

            if or_dimensions:
                or_dims_list = list(itertools.product(*or_dimensions))

                for or_dims_tuple in or_dims_list:
                    extracted_dimensions = sub_dimensions.copy()

                    for dims in iter(or_dims_tuple):
                        for k, v in dims.iteritems():
                            extracted_dimensions[k] = v

                    query = self._build_metrics_query(tenant_id, region, name,
                                                      extracted_dimensions, offset,
                                                      limit)

                    futures.append(self.session.execute_async(query[0], query[1]))

            else:
                query = self._build_metrics_query(tenant_id, region, name, sub_dimensions, offset,
                                                  limit)
                futures.append(self.session.execute_async(query[0], query[1]))

        else:
            query = self._build_metrics_query(tenant_id, region, name, dimensions, offset, limit)
            futures.append(self.session.execute_async(query[0], query[1]))

        metric_list = {}

        for future in futures:
            rows = future.result()
            for row in rows:
                dimensions = {}

                for d in row.dimensions:
                    pair = d.split('=')
                    dimensions[urllib.unquote_plus(pair[0])] = urllib.unquote_plus(pair[1])

                metric = {}
                metric['dimensions'] = dimensions
                metric['id'] = '0x%s' % binascii.hexlify(bytearray(row.metric_id))
                metric['name'] = row.metric_name
                metric_list[metric['id']] = metric

        return sorted(metric_list.values(), key=lambda metric: metric[u'id'])

    def _build_metrics_query(self, tenant_id, region, name, dimensions, offset, limit):

        conditions = [REGION_EQ, TENANT_EQ]
        params = [region, tenant_id.encode('utf8')]

        if name:
            conditions.append(METRIC_NAME_EQ)
            params.append(name)
        else:
            conditions.append('')

        if dimensions:
            conditions.append(DIMENSION_CONTAINS * len(dimensions))
            params.extend(
                [self._create_dimension_value_entry(dim_name, dim_value)
                 for dim_name, dim_value in dimensions.items()])
        else:
            conditions.append('')

        if offset:
            conditions.append(OFFSET_ID_GT % offset)
        else:
            conditions.append('')

        if limit:
            conditions.append(LIMIT_CLAUSE)
            params.append(limit)
        else:
            conditions.append('')

        if (not name) or dimensions:
            conditions.append(ALLOW_FILTERING)
        else:
            conditions.append('')

        return METRIC_LIST_CQL % tuple(conditions), params

    def _create_dimension_value_entry(self, name, value):
        return '%s=%s' % (name, value)

    def list_metric_names(self, tenant_id, region, dimensions):

        try:
            if dimensions:
                futures = []
                for name, value in dimensions.items():
                    futures.append(self.session.execute_async(self.metric_name_by_dimension_stmt,
                                                              [region, tenant_id, name, value]))
                nameSets = []
                for future in futures:
                    rows = future.result()
                    tmp = set()
                    for row in rows:
                        tmp.add(row.metric_name)

                    nameSets.append(tmp)

                names = [{u'name': v} for v in set.intersection(*nameSets)]

            else:
                names = []
                rows = self.session.execute(self.metric_name_stmt, [region, tenant_id])

                for row in rows:
                    names.append({u'name': row.metric_name})

            names.sort(key=lambda x: x[u'name'])

            return names

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def measurement_list(self, tenant_id, region, name, dimensions,
                         start_timestamp, end_timestamp, offset, limit,
                         merge_metrics_flag,
                         group_by):
        metrics = self.list_metrics(tenant_id, region, name, dimensions, None, None)

        return self._measurement_list(metrics, dimensions, start_timestamp, end_timestamp, offset, limit,
                                      merge_metrics_flag, group_by)

    def _measurement_list(self, metrics, dimensions, start_timestamp, end_timestamp, offset, limit, merge_metrics_flag,
                          group_by):

        if not metrics:
            return None
        elif len(metrics) > 1:
            if not merge_metrics_flag and not group_by:
                raise exceptions.MultipleMetricsException(self.MULTIPLE_METRICS_MESSAGE)

        if offset:
            tmp = offset.split(",")
            if len(tmp) > 1:
                offset_id = tmp[0]
                offset_timestamp = tmp[1]
            else:
                offset_id = None
                offset_timestamp = offset
        else:
            offset_timestamp = None
            offset_id = None

        if len(metrics) > 1 and merge_metrics_flag:
            count, series_list = self.query_merge_measurements(metrics,
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

            count, series_list = self.query_measurements(metrics,
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
                sub_count, results = self.query_merge_measurements(sublist,
                                                                   sublist[0]['dimensions'],
                                                                   start_timestamp,
                                                                   end_timestamp,
                                                                   offset_timestamp,
                                                                   limit)
            else:
                sub_count, results = self.query_merge_measurements(sublist,
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

    def query_merge_measurements(self, metrics, dimensions, start_timestamp, end_timestamp,
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

    def query_measurements(self, metrics, start_timestamp, end_timestamp,
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

        conditions = [METRIC_ID_EQ % metric_id]
        params = []

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
                # ' ' ensures missing dimension is sorted lower
                value = metric['dimensions'].get(name, ' ')
                if value != ' ':
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
        return []

    def alarm_history(self, tenant_id, alarm_id_list,
                      offset, limit, start_timestamp, end_timestamp):
        return []
