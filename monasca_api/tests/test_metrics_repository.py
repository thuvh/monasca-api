# Copyright 2018 Hewlett Packard Enterprise Development LP
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
import mock

from monasca_api.common.repositories.influxdb import metrics_repository
from monasca_api.tests import base
from monasca_api.v2.reference import helpers


class MockResponse(object):
    def __init__(self, json_data, status_code):
        self.raw = json_data
        self.status_code = status_code


class InfluxDBClient(object):
    def __init__(self, *args, **kwargs):
        pass

    def query(self, q):
        if q == 'SHOW DIAGNOSTICS':
            response = {u'series': [{
                u'values': [[u'HEAD', u'', u'123', u'0.11.5']],
                u'name': u'build',
                u'columns': [u'Branch', u'Build Time', u'Commit', u'Version']}]}
            return MockResponse(response, 200)
        if q == 'select mean(value)  from  "cpu.utilization"  where _tenant_id = \'1\'' \
                '  and _region = \'USA\'  and time >= 1484036107860000u group by ' \
                'time(300s) fill(none) limit 10001  slimit 1':
            response = {u'series': [{
                u'values': [[u'1970-01-01T00:00:00Z', 0.047]],
                u'name': u'cpu.utilization',
                u'columns': [u'time', u'mean']}],
                u'statement_id': 0}
            return MockResponse(response, 200)
        return MockResponse({}, 404)


class TestMetricsRepo(base.BaseTestCase):

    @classmethod
    @mock.patch('monasca_api.common.repositories.influxdb.metrics_repository.client.InfluxDBClient',
                new=InfluxDBClient)
    def setUpClass(cls):
        cls.mr = metrics_repository.MetricsRepository()

    @mock.patch('monasca_api.common.repositories.influxdb.metrics_repository.client.InfluxDBClient',
                new=InfluxDBClient)
    def test_metrics_statistics(self):
        tenant_id = '1'
        region = 'USA'
        name = 'cpu.utilization'
        start_timestamp = helpers._convert_time_string('2017-01-10T08:15:07.86Z')
        statistics = [u"avg"]
        limit = 10000
        dimensions = None
        end_timestamp = None
        period = None
        offset = None
        merge_metrics_flag = None
        group_by = None

        stats_list = self.mr.metrics_statistics(tenant_id, region, name,
                                                dimensions, start_timestamp,
                                                end_timestamp, statistics,
                                                period, offset, limit,
                                                merge_metrics_flag, group_by)
        expected_result = [{
            u'columns': [u'timestamp', u'avg'],
            u'dimensions': {},
            u'id': '0',
            u'name': u'cpu.utilization',
            u'statistics': [[u'1970-01-01T00:00:00Z', 0.047]]}]
        self.assertEqual(stats_list, expected_result)
