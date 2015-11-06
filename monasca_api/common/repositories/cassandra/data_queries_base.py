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

import abc
from datetime import datetime
from cassandra.util import datetime_from_uuid1
from cassandra.util import min_uuid_from_time
import math
import pytz
import six

# ------------------------
# Abstract Base Class


@six.add_metaclass(abc.ABCMeta)
class DataQuery(object):
    """Abstract base class that defines API access to
       Cassandra data models
    """

    def __init__(self, tenant_id, region, table_name,
                 key_extractor):

        self.tenant_id = tenant_id
        self.region = region
        self.table_name = table_name
        self.key_extractor = key_extractor
        super(DataQuery, self).__init__()

    def build(self, fields, name, dimensions, limit):

        allow_filter_clause = ''

        query = "SELECT %s FROM %s" % (fields, self.table_name)

        query += ' WHERE tenant_id = %s AND region = %s'
        params = [(self.tenant_id.encode('utf8')),
                  (self.region.encode('utf8'))]

        if name:
            query += ' AND NAME = %s'
            params.append(name.encode('utf8'))

        if dimensions:
            allow_filter_clause = ' ALLOW FILTERING'
            for k, v in dimensions.iteritems():
                query += ' AND dimensions CONTAINS %s'
                params.append(k.encode('utf8') + '=' + v.encode('utf8'))

        limit_clause = ''

        if limit:
            limit_clause = ' LIMIT %d' % (limit + 1)

        return query, limit_clause, allow_filter_clause, params

    @staticmethod
    def datetimestr_from_uuid1(time_uuid):
        dt = datetime_from_uuid1(time_uuid).replace(
            tzinfo=pytz.timezone('UTC'))

        # timestamps have millisecond resolution. We display an ISO8601
        # time format with just three decimal places. To the right of
        # three decimal places should be zero in the db, but be sure to
        # take the floor (not round), just in case, to prevent overflow
        # (for example 999500 microseconds should be 999 milliseconds,
        # not 1000)

        return dt.strftime('%Y-%m-%dT%H:%M:%S') + \
            '.%03d' % math.floor(dt.microsecond / 1000.0) + 'Z'

    @staticmethod
    def unpack_dims(dims_list):
        dims_dict = dict()
        for kv in dims_list:
            parts = kv.split('=')
            dims_dict[parts[0]] = parts[1] if len(parts) == 2 else None

        return dims_dict

    @staticmethod
    def build_time_offset_clause(start_timestamp, end_timestamp,
                                 offset_uuid):
        """builds a CQL selection clause based on optional
           start and end timestamps. Comparison is:
           start_timestamp <= t < end_timestamp
        """

        # We are storing time in Cassandra as timeuuid to allow
        # multiple data points with the same timestamp.

        time_clause = ''
        params = []
        comparator = '>'
        start_timeuuid = start_dt = None

        if offset_uuid:
            # the offset should come in as a time uuid (of the last
            # result returned from the previous query). The comparator
            # should be '>', starting at the next record, not
            # including the last record of the previous query.

            start_timeuuid = offset_uuid
            start_dt = datetime_from_uuid1(start_timeuuid).replace(
                tzinfo=pytz.timezone('UTC'))

        if start_timestamp:
            # If there is a start timestamp, the comparator should
            # be '>='. Allow the offset to override the start
            # timestamp, but only if it is >= the start timestamp

            ts_uuid = min_uuid_from_time(start_timestamp)
            ts_dt = datetime.utcfromtimestamp(start_timestamp). \
                replace(tzinfo=pytz.timezone('UTC'))

            if not start_dt or ts_dt > start_dt:
                start_timeuuid = ts_uuid
                comparator = '>='

        if start_timeuuid:
            time_clause += ' AND time ' + comparator + ' %s'
            params.append(start_timeuuid)

        if end_timestamp:
            end_timestampuuid = min_uuid_from_time(end_timestamp)
            time_clause += ' AND time < %s'
            params.append(end_timestampuuid)

        return time_clause, params

    @staticmethod
    def insert_offset_field(results, limit):

        if len(results) > limit:
            results[limit - 1][u'_offset'] = \
                '_'.join([results[limit - 1][u'id'], results[limit - 1][u'name']])

    @staticmethod
    def insert_offset_field_alt(results, limit, raw_results, index):

        if len(results) > limit:
            results[limit - 1][u'_offset'] = \
                '_'.join([results[limit - 1][u'id'], raw_results[limit - 1][index]])

    @abc.abstractmethod
    def build_query(self, *args):
        """Creates the table for the data model
        """
        return '', ()

    @abc.abstractmethod
    def extract_results(self, *args):
        """creates a tuple of the params ordered correctly for
           the INSERT / UPDATE statement.
        """
        return []

    def extract_keys(self, raw_results):
        """creates a tuple of the params ordered correctly for
           the INSERT / UPDATE statement.
        """

        return map(self.key_extractor, raw_results)
