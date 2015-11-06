# -*- coding: utf8 -*-
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

from cassandra.cluster import Cluster
from cassandra.util import datetime_from_uuid1
from cassandra.util import min_uuid_from_time
from common.repositories.cassandra.data_queries_metrics import MeasurementsQueryOne
from common.repositories.cassandra.data_queries_metrics import MetricsQueryByDim
from common.repositories.cassandra.data_queries_metrics import MetricsQueryByName
from common.repositories.cassandra.data_queries_metrics import NamesQuery
from common.repositories import constants
import json
import math
from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories import metrics_repository
from oslo_config import cfg
from oslo_log import log
import pytz
import uuid

LOG = log.getLogger(__name__)


class MetricsRepository(metrics_repository.MetricsRepository):

    INV_MEASURE_OFFSET_MESSAGE = "The offset provided is invalid"

    def __init__(self):

        try:
            self.conf = cfg.CONF
            c = self.conf.cassandra

            contact_points = [x.strip() for x in c.contact_points.split(',')]

            # TODO(msbielinski): does Cassandra 3.0 use protocol_version=4?
            self._cluster = Cluster(contact_points=contact_points,
                                    port=int(c.port), protocol_version=3)
            self._session = self._cluster.connect(c.keyspace_name)

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    @staticmethod
    def _validate_offset(offset_str, dims_str_list, merge_metrics):
        """Break an offset string (if not empty) into its
           components
        """

        if not offset_str:
            return 0, None, None

        else:
            try:
                if not merge_metrics:
                    # When not merge_metrics, the offset contains
                    # only a time UUID for the single metric

                    return 0, uuid.UUID(offset_str), dims_str_list[0]

                else:
                    # When merge_metrics, the offset contains both
                    # a time UUID (or '' if not needed) and the
                    # string representation of the dimensions to
                    # uniquely identify a metric

                    parts = offset_str.split('_', 1)
                    if len(parts) == 2:
                        offset_id = dims_str_list.index(parts[1])
                        return offset_id, \
                            uuid.UUID(parts[0]) if parts[0] else None, \
                            dims_str_list[offset_id]

            except:
                pass

        raise exceptions.RepositoryException(
            MetricsRepository.INV_MEASURE_OFFSET_MESSAGE)

    @staticmethod
    def _make_offset(offset_list, merge_metrics):
        """make an offset string from a list of components
        """

        if not offset_list:
            return None

        elif not merge_metrics:
            # When not merge_metrics, the offset contains
            # only a time UUID for the single metric

            return offset_list[0]

        else:
            # When merge_metrics, the offset contains both
            # a time UUID (or '' if not needed) and the
            # string representation of the dimensions to
            # uniquely identify a metric

            return '_'.join(offset_list)

    @staticmethod
    def _list_metrics_ex(tenant_id, region, name, dimensions,
                         offset, limit):

        if name:
            metrics_query = MetricsQueryByName(tenant_id, region)
            offset_id, query, params = metrics_query.build_query(
                name, dimensions, offset, limit)

        else:
            metrics_query = MetricsQueryByDim(tenant_id, region)
            offset_id, query, params = metrics_query.build_query(
                dimensions, offset, limit)

        return metrics_query, offset_id, query, params

    def _match_metrics(self, tenant_id, region, name,
                       dimensions, merge_metrics):
        """Return a list of matching metrics from a name and
           list of dimensions. Raise an exception if multiple
           metrics match and not merge_metrics
        """
        if not merge_metrics:
            keys_limit = 1
            keys_mess = MetricsRepository.MULTIPLE_METRICS_MESSAGE

        else:
            keys_limit = constants.PAGE_LIMIT
            keys_mess = MetricsRepository.TOO_MANY_METRICS_MESSAGE

        metrics_query, offset_id, query, params = \
            self._list_metrics_ex(tenant_id, region, name,
                                  dimensions, None, keys_limit)

        raw_results = self._session.execute(query, parameters=params)

        if len(raw_results) > keys_limit:
            raise exceptions.RepositoryException(keys_mess)

        keys = metrics_query.extract_keys(raw_results)
        dims_str_list = [k.split(';', 1)[1] for k in keys]

        return dims_str_list

    # TODO(msbielinski): This has been migrated to the DataQuery class and can
    # TODO(msbielinski): be deprecated here

    @staticmethod
    def _build_time_offset_clause(start_timestamp, end_timestamp, offset_uuid, limit):
        """builds a CQL selection clause based on optional
           start and end timestamps. Comparison is:
           start_timestamp <= t < end_timestamp
        """

        # We are storing time in Cassandra as timeuuid to allow multiple data points
        # with the same timestamp.

        time_clause = limit_clause = ''
        start_timeuuid = None

        if offset_uuid:
            # the offset should come in as a time uuid (of the last result returned
            # from the previous query). The comparator should be '>', starting at
            # the next record, not including the last record of the previous query.

            start_timeuuid = uuid.UUID(offset_uuid)
            # try:
            #     start_timeuuid = uuid.UUID(offset_uuid)
            # except ValueError:
            #     start_timeuuid = uuid_from_time(iso8601.parse_date(offset_uuid))

        if start_timestamp:
            # If there is a start timestamp, the comparator should be '>='.
            # Allow the offset to override the start timestamp, but only if
            # it is >= the start timestamp

            ts_uuid = min_uuid_from_time(start_timestamp)
            if not start_timeuuid or ts_uuid > start_timeuuid:
                start_timeuuid = ts_uuid

        if start_timeuuid:
            time_clause += ' AND time >= %s' % str(start_timeuuid)

        if end_timestamp:
            end_timestampuuid = min_uuid_from_time(end_timestamp)
            time_clause += ' AND time < ' + str(end_timestampuuid)

        if limit:
            limit_clause = ' LIMIT %d' % (limit + 1)

        return time_clause, limit_clause

    def list_metrics(self, tenant_id, region, name, dimensions,
                     offset, limit):
        """Handler for endpoint: GET /v2.0/metrics
        """

        try:
            metrics_query, offset_id, query, params = self._list_metrics_ex(
                tenant_id, region, name, dimensions, offset, limit)

            raw_results = self._session.execute(query, parameters=params)

            results = metrics_query.extract_results(
                offset_id, raw_results, limit)

            return results

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def measurement_list(self, tenant_id, region, name, dimensions,
                         start_timestamp, end_timestamp, offset,
                         limit, merge_metrics_flag):
        """Handler for endpoint: GET /v2.0/metrics/measurements
        """

        # NOTE: the way in which this method handles multiple
        # metrics with the merge_metrics_flag is inconsistent
        # with InfluxDB's handling of the same.

        # This difference will need to be addressed prior to
        # release. It's a non-trivial issue with Cassandra.

        try:
            json_measurement_list = []

            dims_str_list = self._match_metrics(tenant_id, region,
                                                name, dimensions,
                                                merge_metrics_flag)

            if len(dims_str_list):

                offset_id, offset_time, offset_dims_str = \
                    self._validate_offset(offset, dims_str_list,
                                          merge_metrics_flag)

                measure_query = MeasurementsQueryOne(tenant_id, region)
                raw_results = []

                # If there is a time component to the offset, it applies
                # only to the metric specified by offset_id. Query for
                # measurements for that metric, and if limit is not hit,
                # then a second query will be needed if multiple metrics

                if offset_time:
                    query, params = measure_query.build_query(
                        name, dims_str_list[offset_id:offset_id + 1],
                        start_timestamp, end_timestamp, offset_time,
                        limit)

                    raw_results += self._session.execute(query, parameters=params)
                    offset_id += 1
                    offset_time = None

                # Possible second query if there are multiple metrics.
                # This will be the first query if no time component to
                # the offset

                rem_limit = limit - len(raw_results)
                if rem_limit >= 0 and offset_id < len(dims_str_list):
                    query, params = measure_query.build_query(
                        name, dims_str_list[offset_id:],
                        start_timestamp, end_timestamp, offset_time,
                        rem_limit)

                    raw_results += self._session.execute(query, parameters=params)

                # extract results from the above query(s)

                json_measurement_list, new_offset = \
                    measure_query.extract_results(
                        name, raw_results, dims_str_list, limit)

                # embed a next offset if required that will
                # be grabbed by the paginator

                if new_offset:
                    json_measurement_list[0][u'_offset'] = self._make_offset(
                        new_offset, merge_metrics_flag)

            return json_measurement_list

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def list_metric_names(self, tenant_id, region, dimensions, offset, limit):
        """Handler for endpoint: GET /v2.0/metrics/names
        """

        try:
            names_query = NamesQuery(tenant_id, region)
            offset_id, query, params = names_query.build_query(dimensions, offset, limit)
            raw_results = self._session.execute(query, parameters=params)
            results = names_query.extract_results(offset_id, raw_results, limit)
            return results

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def metrics_statistics(self, tenant_id, region, name, dimensions,
                           start_timestamp,
                           end_timestamp, statistics, period, offset, limit,
                           merge_metrics_flag):
        """Handler for endpoint: GET /v2.0/metrics/statistics
        """

        try:

            json_statistics_list = []
            return json_statistics_list

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    # @staticmethod
    # def test_uuid():
    #     start_time = '2015-09-04T22:04:42Z'
    #     end_time = '2015-09-04T22:04:42Z'
    #     test_time = '2015-09-04T22:04:42.993000Z'
    #
    #     start_timeuuid = min_uuid_from_time(iso8601.parse_date(start_time))
    #     end_timeuuid = max_uuid_from_time(iso8601.parse_date(end_time))
    #
    #     i = 0
    #     fails = fails_high = fails_low = 0
    #     while i < 1000:
    #         timeuuid = uuid_from_time(iso8601.parse_date(test_time))
    #         if start_timeuuid <= timeuuid <= end_timeuuid:
    #             pass
    #         elif start_timeuuid <= timeuuid:
    #             fails_high += 1
    #             fails += 1
    #         else:
    #             fails_low += 1
    #             fails += 1
    #         i += 1
    #     return fails

    def alarm_history(self, tenant_id, alarm_id_list,
                      offset, limit, start_timestamp=None,
                      end_timestamp=None):
        """Handler for endpoint: GET /v2.0/alarms/state-history
           Handler for endpoint: GET /v2.0/alarms/{{ alarm_id }}/state-history
        """

        try:
            json_alarm_history_list = []

            if not alarm_id_list:
                return json_alarm_history_list

            params = [(tenant_id.encode('utf8'))]
            query = "SELECT " \
                    "  time, alarm_id, metrics, new_state, old_state, " \
                    "  reason, reason_data, sub_alarms, tenant_id " \
                    "FROM alarm_state_hist"

            where_clause = " WHERE tenant_id = %s "

            alarm_id_where_clause = ' alarm_id IN (' + ','.join(['%s'] * len(alarm_id_list)) + ') '
            params += alarm_id_list

            where_clause += ' AND ' + alarm_id_where_clause

            time_clause, limit_clause = self._build_time_offset_clause(
                start_timestamp, end_timestamp, offset, limit)

            # TODO(msbielinski): Order by time
            # "title": "The repository was unable to process your request",
            # "description": "code=2200 [Invalid query] message=\"Cannot page queries
            # with both ORDER BY and a IN restriction on the partition key; you must
            # either remove the ORDER BY or the IN and sort client side, or disable
            # paging for this query\""
            # order_clause = ' ORDER BY time'
            order_clause = ''

            # offset_clause = self._build_offset_clause(offset, limit)
            query += where_clause + time_clause + order_clause + limit_clause
            # query_str = query.replace("%s", "'%s'") % tuple(params)
            result = self._session.execute(query, parameters=tuple(params))

            if not result:
                return json_alarm_history_list

            for point in result:
                dt = datetime_from_uuid1(point[0]).replace(tzinfo=pytz.timezone('UTC'))

                # timestamps have millisecond resolution. We display an ISO8601
                # time format with just three decimal places. To the right of
                # three decimal places should be zero in the db, but be sure to
                # take the floor (not round), just in case, to prevent overflow
                # (for example 999500 microseconds should be 999 milliseconds,
                # not 1000)

                iso4 = dt.strftime('%Y-%m-%dT%H:%M:%S') + \
                    '.%03d' % math.floor(dt.microsecond / 1000.0) + 'Z'

                # the timeuuid also serves as the unique ID.

                alarm_point = {u'id': str(point[0]),
                               u'timestamp': iso4,
                               u'alarm_id': point[1],
                               u'metrics': json.loads(point[2]),
                               u'new_state': point[3],
                               u'old_state': point[4],
                               u'reason': point[5],
                               u'reason_data': point[6],
                               u'sub_alarms': json.loads(point[7]),
                               u'tenant_id': point[8]}

                # java api formats these during json serialization
                if alarm_point[u'sub_alarms']:
                    for sub_alarm in alarm_point[u'sub_alarms']:
                        sub_expr = sub_alarm['sub_alarm_expression']
                        metric_def = sub_expr['metric_definition']
                        sub_expr['metric_name'] = metric_def['name']
                        sub_expr['dimensions'] = metric_def['dimensions']
                        del sub_expr['metric_definition']

                json_alarm_history_list.append(alarm_point)

            return json_alarm_history_list

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)
