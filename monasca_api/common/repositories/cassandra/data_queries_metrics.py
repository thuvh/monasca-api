#!/usr/bin/env python
# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json

from common.repositories.cassandra.data_queries_base import DataQuery


class NamesQuery(DataQuery):

    def __init__(self, tenant_id, region):
        super(NamesQuery, self).__init__(
            tenant_id, region, 'metrics_name_only', None)

    def build_query(self, dimensions, offset, limit):
        offset_id = 1
        query, limit_clause, allow_filter_clause, params = self.build(
            'name', None, dimensions, limit)

        if offset:
            parts = offset.split('_', 1)
            offset_id = int(parts[0]) + 1
            query += ' AND name > %s'
            params += [parts[1]]

        query += limit_clause + allow_filter_clause
        return offset_id, query, tuple(params)

    def extract_results(self, offset_id, raw_results, limit):
        results = []
        for raw_one in raw_results:
            results.append({u'id': str(offset_id), u'name': raw_one[0]})
            offset_id += 1

        if len(results) > limit:
            results[limit - 1][u'_offset'] = \
                '_'.join([results[limit - 1][u'id'], results[limit - 1][u'name']])

        return results


class MetricsQueryByName(DataQuery):

    def __init__(self, tenant_id, region):
        key_extractor = lambda x: ';'.join(x[0:2])
        super(MetricsQueryByName, self).__init__(
            tenant_id, region, 'metrics_name', key_extractor)

    def build_query(self, name, dimensions, offset, limit):
        offset_id = 1
        allow_filter_clause = ''

        query = 'SELECT name, dims_str, dimensions FROM %s' % self.table_name

        query += ' WHERE tenant_id = %s AND region = %s AND name = %s'
        params = [(self.tenant_id.encode('utf8')), (self.region.encode('utf8')),
                  name.encode('utf8')]

        if dimensions:
            allow_filter_clause = ' ALLOW FILTERING'
            for k, v in dimensions.iteritems():
                query += ' AND dimensions CONTAINS %s'
                params.append(k.encode('utf8') + '=' + v.encode('utf8'))

        if offset:
            parts = offset.split('_', 1)
            offset_id = int(parts[0]) + 1
            query += ' AND dims_str > %s'
            params += [parts[1]]

        limit_clause = ''

        if limit:
            limit_clause = ' LIMIT %d' % (limit + 1)

        query += limit_clause + allow_filter_clause
        return offset_id, query, tuple(params)

    def extract_results(self, offset_id, raw_results, limit):
        results = []
        for raw_one in raw_results:
            results.append({
                u'id': str(offset_id),
                u'name': raw_one[0],
                u'dimensions': self.unpack_dims(raw_one[2])
            })
            offset_id += 1

        self.insert_offset_field_alt(results, limit, raw_results, 1)
        return results


class MetricsQueryByDim(DataQuery):

    def __init__(self, tenant_id, region):
        key_extractor = lambda x: x[0]
        super(MetricsQueryByDim, self).__init__(
            tenant_id, region, 'metrics_dim', key_extractor)

    def build_query(self, dimensions, offset, limit):
        offset_id = 1
        allow_filter_clause = ''

        query = 'SELECT name_dims, dimensions FROM %s' % self.table_name
        query += ' WHERE tenant_id = %s AND region = %s AND key_dim = %s'

        key_dim = '%s=%s' % dimensions.popitem() if dimensions else ''
        params = [(self.tenant_id.encode('utf8')), (self.region.encode('utf8')),
                  key_dim.encode('utf8')]

        if dimensions:
            allow_filter_clause = ' ALLOW FILTERING'
            for k, v in dimensions.iteritems():
                query += ' AND dimensions CONTAINS %s'
                params.append(k.encode('utf8') + '=' + v.encode('utf8'))

        if offset:
            parts = offset.split('_', 1)
            offset_id = int(parts[0]) + 1
            query += ' AND name_dims > %s'
            params += [parts[1]]

        limit_clause = ''

        if limit:
            limit_clause = ' LIMIT %d' % (limit + 1)

        query += limit_clause + allow_filter_clause
        return offset_id, query, tuple(params)

    def extract_results(self, offset_id, raw_results, limit):
        results = []
        for raw_one in raw_results:
            name, dim_str = raw_one[0].split(';', 1)
            results.append({
                u'id': str(offset_id),
                u'name': name,
                u'dimensions': self.unpack_dims(raw_one[1])
            })

            offset_id += 1

        self.insert_offset_field_alt(results, limit, raw_results, 0)
        return results


class MeasurementsQueryOne(DataQuery):
    # cqlcmd = "CREATE TABLE measurements (" \
    #          "  tenant_id text, " \
    #          "  region text, " \
    #          "  name text, " \
    #          "  dims_str text, " \
    #          "  time timeuuid, " \
    #          "  value double, " \
    #          "  value_meta text, " \
    #          "  PRIMARY KEY ((tenant_id, region, name), dims_str, time)" \
    #          ");"

    def __init__(self, tenant_id, region):
        key_extractor = None
        super(MeasurementsQueryOne, self).__init__(
            tenant_id, region, 'measurements_dim', key_extractor)

    def build_query(self, name, dims_str_list, start_timestamp,
                    end_timestamp, offset, limit):

        query = 'SELECT dims_str, time, value, value_meta FROM %s' \
                % self.table_name

        query += ' WHERE tenant_id = %s AND region = %s' \
                 ' AND name = %s'

        params = [(self.tenant_id.encode('utf8')), (self.region.encode('utf8')),
                  name.encode('utf8')]

        # AND dims_str = %s'

        if dims_str_list:
            query += ' AND dims_str in (' + ','.join(
                ['%s'] * len(dims_str_list)) + ')'
            params += [ds.encode('utf8') for ds in dims_str_list]

        offset_clause, offset_params = self.build_time_offset_clause(
            start_timestamp, end_timestamp, offset)

        query += offset_clause
        params += offset_params

        if limit is not None:
            query += ' LIMIT %d' % (limit + 1)

        # allow_filter_clause = ''
        # query += allow_filter_clause

        return query, tuple(params)

    def extract_results(self, name, raw_results,
                        dims_str_list, limit):
        results = []
        limit_hit = cur_rec = None
        last_dims_str = last_time_uuid = None
        offset_id = n = 0
        columns_list = [u'timestamp', u'value', u'value_meta']

        for raw_one in raw_results:

            cur_dims_str = raw_one[0]
            if cur_dims_str != last_dims_str:
                last_time_uuid = None
                offset_id = dims_str_list.index(cur_dims_str)

            if n >= limit:
                limit_hit = (str(last_time_uuid or ''),
                             cur_dims_str)
                break

            if cur_dims_str != last_dims_str:
                dims = {} if not cur_dims_str \
                    else self.unpack_dims(cur_dims_str.split(';'))

                cur_rec = {u'name': name,
                           u'id': offset_id + 1,
                           u'dimensions': dims,
                           u'columns': columns_list,
                           u'measurements': []
                           }

                last_dims_str = cur_dims_str
                results.append(cur_rec)

            cur_rec[u'measurements'].append([
                self.datetimestr_from_uuid1(raw_one[1]),
                raw_one[2],
                json.loads(raw_one[3] or '{}')
            ])
            last_time_uuid = raw_one[1]
            n += 1

        return results, limit_hit
