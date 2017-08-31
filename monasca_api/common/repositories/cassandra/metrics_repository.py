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
from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories import metrics_repository
from monasca_common.rest import utils as rest_utils
from oslo_config import cfg
from oslo_log import log

LOG = log.getLogger(__name__)


class MetricsRepository(metrics_repository.AbstractMetricsRepository):
    def __init__(self):

        try:
            self.conf = cfg.CONF
            self.cluster = Cluster(self.conf.cassandra.contactPoints)
            self.session = self.cluster.connect(self.conf.cassandra.keyspace)

            self.dim_val_by_metric_stmt = self.session.prepare(
                "select dimension_value as value from metrics_dimensions where "
                + "region = ? and tenant_id = ? and metric_name = ? and dimension_name = ?"
                + "group by dimension_value")

            self.dim_val_stmt = self.session.prepare(
                "select value from dimensions "
                + "where region = ? and tenant_id = ? and name = ? "
                + "group by value order by value")

            self.dim_name_by_metric_stmt = self.session.prepare(
                "select dimension_name as name from metrics_dimensions where "
                + "region = ? and tenant_id = ? and metric_name = ? "
                + "group by dimension_name order by dimension_name")

            self.dim_name_stmt = self.session.prepare(
                "select name from dimensions where region = ? and tenant_id = ? "
                + "group by name allow filtering")

            self.metric_name_by_dimension_stmt = self.session.prepare(
                "select metric_name from dimensions_metrics where region = ? and "
                + "tenant_id = ? and dimension_name = ? and dimension_value = ?"
                + "group by metric_name order by metric_name")

            self.metric_name_stmt = self.session.prepare(
                "select distinct region, tenant_id, metric_name from metrics_dimensions "
                + "where region = ? and tenant_id = ? allow filtering")

            self.measurement_sql = ('select time_stamp, value, value_meta '
                                    'from measurements where %s %s %s %s')
            self.metric_id_eq = 'metric_id = %s'
            self.metric_id_in = 'metric_id in %s'
            self.offset_time_condition = "and times_tamp > %s"
            self.start_time_condition = "and time_stamp >= %s"
            self.end_time_condition = "and time_stamp <= %s"

            self.metric_sql = ('select metric_name, dimensions, metric_id '
                               'from metrics '
                               'where %s %s %s %s %s %s %s %s %s')
            self.region_condition = 'region = %s'
            self.tenant_condition = 'and tenant_id = %s'
            self.metric_name_condition = 'and metric_name = %s'
            self.dimension_condition = 'and dimensions contains %s'
            self.offset_condition = 'and metric_id > %s'
            self.created_at_condition = 'and created_at < %s'
            self.updated_at_condition = 'and updated_at > %s'
            self.limit_clause = 'limit %s'
            self.allow_filtering = 'allow filtering'

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
                sorted = True
            else:
                rows = self.session.execute(
                    self.dim_name_stmt,
                    [region, tenant_id])
                sorted = False

            json_dim_name_list = []

            if not rows:
                return json_dim_name_list

            for row in rows:
                json_dim_name_list.append({u'dimension_name': row.name})

            json_dim_name_list.sort(key=lambda x: x[u'dimension_name'])

            return json_dim_name_list
        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def list_metrics(self, tenant_id, region, name, dimensions, offset,
                     limit, start_timestamp=None, end_timestamp=None):
        or_dimensions = []
        sub_dimensions = {}
        futures = []

        if dimensions:
            for key, value in dimensions.items():
                if not value:
                    # does not support search by key only
                    LOG.INFO('Ignored search by dimension key only in dimension dictionary: %s' % dimensions)

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
                                                      limit, start_timestamp,
                                                      end_timestamp)

                    futures.append(self.session.execute_async(query[0], query[1]))

            else:
                query = self._build_metrics_query(tenant_id, region, name, sub_dimensions, offset,
                                                  limit, start_timestamp, end_timestamp)
                futures.append(self.session.execute_async(query[0], query[1]))

        else:
            query = self._build_metrics_query(tenant_id, region, name, dimensions, offset,
                                              limit, start_timestamp, end_timestamp)
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

    def _build_metrics_query(self, tenant_id, region, name, dimensions, offset,
                             limit, start_timestamp=None, end_timestamp=None):

        conditions = [self.region_condition, self.tenant_condition]
        params = [region, tenant_id.encode('utf8')]

        if name:
            conditions.append(self.metric_name_condition)
            params.append(name)
        else:
            conditions.append('')

        if dimensions:
            conditions.append(self.dimension_condition * len(dimensions))
            params.extend([self._create_dimension_value_entry(name, value) for name, value in dimensions.items()])
        else:
            conditions.append('')

        if offset:
            conditions.append(self.offset_condition % offset)
        else:
            conditions.append('')

        if start_timestamp:
            if end_timestamp:
                conditions.append(self.created_at_condition)
                params.append(int(end_timestamp) * 1000)
            else:
                conditions.append('')

            conditions.append(self.updated_at_condition)
            params.append(int(start_timestamp) * 1000)
        else:
            conditions.append('')
            conditions.append('')

        if limit:
            conditions.append(self.limit_clause)
            params.append(limit)
        else:
            conditions.append('')

        if (not name) or dimensions:
            conditions.append(self.allow_filtering)
        else:
            conditions.append('')

        return self.metric_sql % tuple(conditions), params

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

            LOG.info('metric name list: %s' % names)

            names.sort(key=lambda x: x[u'name'])

            return names

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def measurement_list(self, tenant_id, region, name, dimensions,
                         start_timestamp, end_timestamp, offset, limit,
                         merge_metrics_flag,
                         group_by):

        metrics = self.list_metrics(tenant_id, region, name, dimensions,
                                    None, None, start_timestamp, end_timestamp)

        LOG.info('metric list: %s' % metrics)
        if not metrics:
            return None

        if offset:
            tmp = offset.split(",")
            offset_id = tmp[0]
            offset_timestamp = tmp[1]
        else:
            offset_timestamp = None
            offset_id = None

        results = []
        if len(metrics) > 1:
            if not merge_metrics_flag and not group_by:
                raise exceptions.MultipleMetricsException(self.MULTIPLE_METRICS_MESSAGE)
            if merge_metrics_flag:
                for metric in metrics:
                    query = self._build_measurement_query(metric['id'],
                                                          start_timestamp,
                                                          end_timestamp,
                                                          offset_timestamp,
                                                          limit)
                    results.append((metric, iter(self.session.execute_async(query[0], query[1]).result())))

            else:
                foundStartMetric = not offset_id
                for metric in metrics:
                    if not foundStartMetric:
                        if metric['id'] == offset_id:
                            foundStartMetric = True
                            query = self._build_measurement_query(offset_id,
                                                                  start_timestamp,
                                                                  end_timestamp,
                                                                  None,
                                                                  limit)
                            results.append(metric, iter(self.session.execute_async(query[0], query[1]).result()))
                        else:
                            continue
                    else:
                        query = self._build_measurement_query(metric['id'],
                                                              start_timestamp,
                                                              end_timestamp,
                                                              None,
                                                              limit)
                        results.append(metric, iter(self.session.execute_async(query[0], query[1]).result()))
        else:
            query = self._build_measurement_query(metrics[0]['id'],
                                                  start_timestamp,
                                                  end_timestamp,
                                                  offset_timestamp,
                                                  limit)
            results.append((metrics[0], iter(self.session.execute_async(query[0], query[1]).result())))

        series_list = []
        count = 0
        if not merge_metrics_flag:
            for result in results:
                measurements = []
                row = next(result[1], None)
                while row:
                    measurements.append([self._isotime_msec(row.time_stamp),
                                         row.value,
                                         rest_utils.from_json(row.value_meta) if row.value_meta else {}])
                    count += 1
                    if count >= limit:
                        break;

                    row = next(result[1], None)

                series_list.append({'name': result[0]['name'],
                                    'id': result[0]['id'],
                                    'columns': ['timestamp', 'value', 'value_meta'],
                                    'measurements': measurements,
                                    'dimensions': result[0]['dimensions']})
                if count >= limit:
                    break;

            return series_list

        else:
            measurements = []
            index = 0;
            top_batch = []
            num_series = len(results)
            for i in range(0, num_series):
                row = next(results[i][1], None)
                if row:
                    top_batch.append([i,
                                      row.time_stamp,
                                      row.value,
                                      rest_utils.from_json(row.value_meta) if row.value_meta else {}])
                else:
                    num_series -= 1

            LOG.info('start top batch: %s' % top_batch)
            top_batch.sort(key=lambda m: m[1], reverse=True)

            while count < limit and top_batch:
                measurements.append([self._isotime_msec(top_batch[num_series - 1][1]),
                                     top_batch[num_series - 1][2],
                                     top_batch[num_series - 1][3]])
                count += 1
                row = next(results[top_batch[num_series - 1][0]][1], None)
                if row:
                    top_batch[num_series - 1] = [top_batch[num_series - 1][0],
                                                 row.time_stamp,
                                                 row.value,
                                                 rest_utils.from_json(row.value_meta) if row.value_meta else {}]

                    top_batch.sort(key=lambda m: m[1], reverse=True)
                else:
                    num_series -= 1
                    top_batch.pop()

                LOG.info('new top batch: %s' % top_batch)

            # LOG.info('tuple print: %s     %s' % (results[0][0], results[0][1]))

            series_list.append({'name': metrics[0]['name'],
                                'id': metrics[0]['id'],
                                'columns': ['timestamp', 'value', 'value_meta'],
                                'measurements': measurements,
                                'dimensions': dimensions})
            LOG.info('series list: %s' % series_list)
            return series_list

    def _build_measurement_query(self, metric_id, start_timestamp, end_timestamp, offset_timestamp, limit):

        conditions = [self.metric_id_eq % metric_id]
        params = []

        if offset_timestamp:
            conditions.append(self.offset_time_condition)
            params.append(offset_timestamp)
        elif start_timestamp:
            conditions.append(self.start_time_condition)
            params.append(int(start_timestamp * 1000))
        else:
            conditions.append('')

        if end_timestamp:
            conditions.append(self.end_time_condition)
            params.append(int(end_timestamp * 1000))
        else:
            conditions.append('')

        if limit:
            conditions.append(self.limit_clause)
            params.append(limit)
        else:
            conditions.append('')

        LOG.info('sql query: %s' % (self.measurement_sql % tuple(conditions)))
        LOG.info('sql params: %s' % params)
        return self.measurement_sql % tuple(conditions), params

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
