# -*- coding: utf-8 -*-
# Copyright 2015 Hewlett-Packard
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
import json
import urllib
import binascii

from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
from oslo_config import cfg
from oslo_log import log

from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories import metrics_repository

LOG = log.getLogger(__name__)


class MetricsRepository(metrics_repository.MetricsRepository):

    def __init__(self):

        try:

            self.conf = cfg.CONF

            self._cassandra_cluster = Cluster(
                    self.conf.cassandra.cluster_ip_addresses.split(','))

            self.cassandra_session = self._cassandra_cluster.connect(
                    self.conf.cassandra.keyspace)

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def list_metrics(self, tenant_id, region, name, dimensions, offset,
                     limit, start_timestamp, end_timestamp,
                     include_metric_hash=False):

        # TODO Use start_timestamp, end_timestamp.

        try:

            select_stmt = """
              select tenant_id, region, metric_hash, metric_set
              from metric_map
              where tenant_id = %s and region = %s
              """

            parms = [tenant_id.encode('utf8'), region.encode('utf8')]

            name_clause = self.build_name_clause(name, parms)

            dimension_clause = self.build_dimensions_clause(dimensions, parms)

            select_stmt += name_clause + dimension_clause

            if offset:

                select_stmt += ' and metric_hash > %s '
                parms.append(bytearray(offset.decode('hex')))

            if limit:

                select_stmt += ' limit %s '
                parms.append(limit + 1)

            select_stmt += ' allow filtering '

            json_metric_list = []

            stmt = SimpleStatement(select_stmt,
                                   fetch_size=2147483647)

            rows = self.cassandra_session.execute(stmt, parms)

            for (tenant_id, region, metric_hash, metric_set) in rows:

                metric = {}

                dimensions = {}

                if include_metric_hash:
                    metric[u'metric_hash'] = metric_hash

                for dimension in metric_set:

                    name, value = dimension.split('=')

                    if name == '__name__':

                        name = urllib.unquote_plus(value)

                        metric[u'name'] = name

                    else:

                        name = urllib.unquote_plus(name)

                        value = urllib.unquote_plus(value)

                        dimensions[name] = value

                metric[u'dimensions'] = dimensions

                metric[u'id'] = binascii.hexlify(bytearray(metric_hash))

                json_metric_list.append(metric)

            return json_metric_list

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def build_dimensions_clause(self, dimensions, parms):

        dimension_clause = ''
        if dimensions:

            for name, value in dimensions.iteritems():
                dimension_clause = (dimension_clause + 'and metric_set '
                                                       'contains %s ')

                parms.append(urllib.quote_plus(name).encode('utf8')
                             + '='.encode('utf8') +
                             urllib.quote_plus(value).encode('utf8'))
        return dimension_clause

    def build_name_clause(self, name, parms):

        name_clause = ''
        if name:
            name_clause = ' and metric_set contains %s '

            parms.append('__name__' + '=' + urllib.quote_plus(name).encode(
                    'utf8'))
        return name_clause

    def measurement_list(self, tenant_id, region, name, dimensions,
                         start_timestamp, end_timestamp, offset,
                         limit, merge_metrics_flag):

        try:

            json_measurement_list = []

            rows = self.get_measurements(tenant_id, region, name, dimensions,
                                         start_timestamp, end_timestamp,
                                         offset, limit, merge_metrics_flag)

            if not rows:
                return json_measurement_list

            measurements_list = (
                [[time_stamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ').decode('utf8'),
                  value,
                  json.loads(value_meta)]
                 for (time_stamp, value, value_meta) in rows])

            measurement = {u'name': name,
                           # The last date in the measurements list.
                           u'id': measurements_list[-1][0],
                           u'dimensions': dimensions,
                           u'columns': [u'timestamp', u'value',u'value_meta'],
                           u'measurements': measurements_list}

            json_measurement_list.append(measurement)

            return json_measurement_list

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def get_measurements(self, tenant_id, region, name, dimensions,
                         start_timestamp, end_timestamp, offset, limit,
                         merge_metrics_flag):

        metric_list = self.list_metrics(tenant_id, region, name,
                                        dimensions, None, None,
                                        start_timestamp, end_timestamp,
                                        include_metric_hash=True)
        if not metric_list:
            return None

        if len(metric_list) > 1:

            if not merge_metrics_flag:

                raise exceptions.MultipleMetricsException(
                    self.MULTIPLE_METRICS_MESSAGE)

        select_stmt = """
          select time_stamp, value, value_meta
          from measurements
          where tenant_id = %s and region = %s
          """

        parms = [tenant_id.encode('utf8'), region.encode('utf8')]

        metric_hash_list = [bytearray(metric['metric_hash']) for metric in
                            metric_list]

        place_holders = ["%s" for x in range(len(metric_hash_list))]

        in_clause = ' and metric_hash in ({}) '.format(",".join(
                place_holders))

        select_stmt += in_clause

        parms.extend(metric_hash_list)

        if offset:

            select_stmt += '  and time_stamp > %s '
            parms.append(offset)

        elif start_timestamp:

            select_stmt += ' and time_stamp >= %s '
            parms.append(int(start_timestamp) * 1000)

        if end_timestamp:

            select_stmt += ' and time_stamp <= %s '
            parms.append(int(end_timestamp) * 1000)

        select_stmt += ' order by time_stamp '

        if limit:

            select_stmt += ' limit %s '
            parms.append(limit + 1)

        stmt = SimpleStatement(select_stmt,
                               fetch_size=2147483647)
        rows = self.cassandra_session.execute(stmt, parms)

        return rows

    def list_metric_names(self, tenant_id, region, dimensions, offset, limit):

        try:

            select_stmt = """
              select metric_hash, metric_set
              from metric_map
              where tenant_id = %s and region = %s
              """

            parms = [tenant_id.encode('utf8'), region.encode('utf8')]

            dimension_clause = self.build_dimensions_clause(dimensions, parms)

            select_stmt += dimension_clause

            if offset:

                select_stmt += ' and metric_hash > %s '
                parms.append(bytearray(offset.decode('hex')))

            if limit:

                select_stmt += ' limit %s '
                parms.append(limit + 1)

            select_stmt += ' allow filtering'

            json_name_list = []

            stmt = SimpleStatement(select_stmt,
                                   fetch_size=2147483647)

            rows = self.cassandra_session.execute(stmt, parms)

            for (metric_hash, metric_set) in rows:

                metric = {}

                for dimension in metric_set:

                    name, value = dimension.split('=')

                    if name == '__name__':

                        name = urllib.unquote_plus(value)

                        metric[u'name'] = name

                        break

                metric[u'id'] = binascii.hexlify(bytearray(metric_hash))

                json_name_list.append(metric)

            return json_name_list

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def metrics_statistics(self, tenant_id, region, name, dimensions,
                           start_timestamp, end_timestamp, statistics,
                           period, offset, limit, merge_metrics_flag):

        try:

            if not period:
                period = 300

            json_statistics_list = []

            rows = self.get_measurements(tenant_id, region, name, dimensions,
                                         start_timestamp, end_timestamp,
                                         offset, limit, merge_metrics_flag)

            if not rows:
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

            first_row = rows[0]
            count = 0
            sum = 0
            start_period = first_row.time_stamp
            max = first_row.value
            min = first_row.value

            stats_list = []
            for (time_stamp, value, value_meta) in rows:

                if (time_stamp - start_period).seconds > period:

                    stat = [start_period.strftime('%Y-%m-%dT%H:%M:%S.%fZ').decode('utf8')]

                    if 'avg' in requested_statistics:

                        stat.append(sum / count)

                    if 'min' in requested_statistics:

                        stat.append(min)

                        min = value

                    if 'max' in requested_statistics:

                        stat.append(max)

                        max = value

                    if 'count' in requested_statistics:

                        stat.append(count)

                    if 'sum' in requested_statistics:

                        stat.append(sum)

                    stats_list.append(stat)

                    start_period = time_stamp

                    sum = 0
                    count = 0

                count = count + 1
                sum = sum + value

                if 'min' in requested_statistics:

                    if value <= min:
                        min = value

                if 'max' in requested_statistics:

                    if value >= max:
                        max = value

            if count:

                stat = [start_period.strftime('%Y-%m-%dT%H:%M:%S.%fZ').decode('utf8')]

                if 'avg' in requested_statistics:

                    stat.append(sum / count)

                if 'min' in requested_statistics:

                    stat.append(min)

                if 'max' in requested_statistics:

                    stat.append(max)

                if 'count' in requested_statistics:

                    stat.append(count)

                if 'sum' in requested_statistics:

                    stat.append(sum)

                stats_list.append(stat)

            statistic = {u'name': name.decode('utf8'),
                         # The last date in the stats list.
                         u'id': stats_list[-1][0],
                         u'dimensions': dimensions,
                         u'columns': columns,
                         u'statistics': stats_list}

            json_statistics_list.append(statistic)

            return json_statistics_list

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def alarm_history(self, tenant_id, alarm_id_list,
                      offset, limit, start_timestamp=None,
                      end_timestamp=None):

        try:

            json_alarm_history_list = []

            if not alarm_id_list:
                return json_alarm_history_list

            select_stmt = """
              select alarm_id, time_stamp, metrics, new_state, old_state,
              reason, reason_data, sub_alarms, tenant_id
              from alarm_state_history
              where tenant_id = %s
              """

            parms = [tenant_id.encode('utf8')]

            place_holders = ["%s" for x in range(len(alarm_id_list))]

            in_clause = ' and alarm_id in ({}) '.format(",".join(place_holders))

            select_stmt += in_clause

            parms.extend(alarm_id_list)

            if offset:

                select_stmt += ' and time_stamp > %s '
                parms.append(offset)

            elif start_timestamp:

                select_stmt += ' and time_stamp >= %s '
                parms.append(int(start_timestamp) * 1000)

            if end_timestamp:

                select_stmt += ' and time_stamp <= %s '
                parms.append(int(end_timestamp) * 1000)

            if limit:

                select_stmt += ' limit %s '
                parms.append(limit + 1)

            stmt = SimpleStatement(select_stmt,
                                   fetch_size=2147483647)


            rows = self.cassandra_session.execute(stmt, parms)

            if not rows:
                return json_alarm_history_list

            for (alarm_id, time_stamp, metrics, new_state, old_state, reason,
                 reason_data, sub_alarms, tenant_id) in rows:

                alarm = {u'timestamp': time_stamp.strftime(
                        '%Y-%m-%dT%H:%M:%S.%fZ').decode('utf8'),
                         u'alarm_id': alarm_id,
                         u'metrics': json.loads(metrics),
                         u'new_state': new_state,
                         u'old_state': old_state,
                         u'reason': reason,
                         u'reason_data': reason_data,
                         u'sub_alarms': json.loads(sub_alarms),
                         u'id': str(int(time_stamp.strftime("%s")) *
                                1000).decode('utf8')}

                if alarm[u'sub_alarms']:
                    for sub_alarm in alarm[u'sub_alarms']:
                        sub_expr = sub_alarm['sub_alarm_expression']
                        metric_def = sub_expr['metric_definition']
                        sub_expr['metric_name'] = metric_def['name']
                        sub_expr['dimensions'] = metric_def['dimensions']
                        del sub_expr['metric_definition']

                json_alarm_history_list.append(alarm)

            return json_alarm_history_list

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)
