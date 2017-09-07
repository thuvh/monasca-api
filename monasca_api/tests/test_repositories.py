# Copyright 2015 Cray Inc. All Rights Reserved.
# (C) Copyright 2016-2017 Hewlett Packard Enterprise Development LP
# Copyright 2017 Fujitsu LIMITED
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

import cassandra
import griddb_python_client as griddb
import influxdb.exceptions as iexc
import mock
from mock import patch

from oslo_config import cfg
from oslo_utils import timeutils

from monasca_api.common.repositories.cassandra import metrics_repository \
    as cassandra_repo
from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories.griddb import metrics_repository \
    as griddb_repo
from monasca_api.common.repositories.influxdb import metrics_repository \
    as influxdb_repo
from monasca_api.tests import base

CONF = cfg.CONF


class TestRepoMetricsInfluxDB(base.BaseTestCase):

    @patch("monasca_api.common.repositories.influxdb."
           "metrics_repository.client.InfluxDBClient")
    def test_measurement_list(self, influxdb_client_mock):
        mock_client = influxdb_client_mock.return_value
        mock_client.query.return_value.raw = {
            "series": [
                {
                    "name": "dummy.series",
                    "values": [
                        ["2015-03-14T09:26:53.59Z", 2, None],
                        ["2015-03-14T09:26:53.591Z", 2.5, ''],
                        ["2015-03-14T09:26:53.6Z", 4.0, '{}'],
                        ["2015-03-14T09:26:54Z", 4, '{"key": "value"}']
                    ]
                }
            ]
        }

        repo = influxdb_repo.MetricsRepository()
        result = repo.measurement_list(
            "tenant_id",
            "region",
            name=None,
            dimensions=None,
            start_timestamp=1,
            end_timestamp=2,
            offset=None,
            limit=1,
            merge_metrics_flag=True,
            group_by=None)

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]['dimensions'])
        self.assertEqual(result[0]['name'], 'dummy.series')
        self.assertEqual(result[0]['columns'],
                         ['timestamp', 'value', 'value_meta'])

        measurements = result[0]['measurements']

        self.assertEqual(
            [["2015-03-14T09:26:53.590Z", 2, {}],
             ["2015-03-14T09:26:53.591Z", 2.5, {}],
             ["2015-03-14T09:26:53.600Z", 4.0, {}],
             ["2015-03-14T09:26:54.000Z", 4, {"key": "value"}]],
            measurements
        )

    @patch("monasca_api.common.repositories.influxdb."
           "metrics_repository.client.InfluxDBClient")
    def test_list_metrics(self, influxdb_client_mock):
        mock_client = influxdb_client_mock.return_value
        mock_client.query.return_value.raw = {
            u'series': [{
                u'values': [[
                    u'disk.space_used_perc,_region=region,_tenant_id='
                    u'0b5e7d8c43f74430add94fba09ffd66e,device=rootfs,'
                    'hostname=host0,hosttype=native,mount_point=/',
                    u'region',
                    u'0b5e7d8c43f74430add94fba09ffd66e',
                    u'rootfs',
                    u'host0',
                    u'native',
                    u'',
                    u'/'
                ]],
                u'name': u'disk.space_used_perc',
                u'columns': [u'_key', u'_region', u'_tenant_id', u'device',
                             u'hostname', u'hosttype', u'extra', u'mount_point']
            }]
        }

        repo = influxdb_repo.MetricsRepository()

        result = repo.list_metrics(
            "0b5e7d8c43f74430add94fba09ffd66e",
            "region",
            name="disk.space_user_perc",
            dimensions={
                "hostname": "host0",
                "hosttype": "native",
                "mount_point": "/",
                "device": "rootfs"},
            offset=None,
            limit=1)

        self.assertEqual(result, [{
            u'id': '0',
            u'name': u'disk.space_used_perc',
            u'dimensions': {
                u'device': u'rootfs',
                u'hostname': u'host0',
                u'mount_point': u'/',
                u'hosttype': u'native'
            },
        }])

    @patch("monasca_api.common.repositories.influxdb."
           "metrics_repository.client.InfluxDBClient")
    def test_list_dimension_values(self, influxdb_client_mock):
        mock_client = influxdb_client_mock.return_value
        mock_client.query.return_value.raw = {
            u'series': [
                {
                    u'values': [[u'custom_host']],
                    u'name': u'custom_metric',
                    u'columns': [u'hostname']
                }]
        }

        repo = influxdb_repo.MetricsRepository()
        mock_client.query.reset_mock()

        result = repo.list_dimension_values(
            "38dc2a2549f94d2e9a4fa1cc45a4970c",
            "useast",
            "custom_metric",
            "hostname")

        self.assertEqual(result, [{u'dimension_value': u'custom_host'}])

        mock_client.query.assert_called_once_with(
            'show tag values from "custom_metric" with key = "hostname"'
            ' where _tenant_id = \'38dc2a2549f94d2e9a4fa1cc45a4970c\''
            '  and _region = \'useast\' ')

    @patch("monasca_api.common.repositories.influxdb."
           "metrics_repository.client.InfluxDBClient")
    def test_list_dimension_names(self, influxdb_client_mock):
        mock_client = influxdb_client_mock.return_value
        mock_client.query.return_value.raw = {
            u'series': [{
                u'values': [[u'_region'], [u'_tenant_id'], [u'hostname'],
                            [u'service']],
                u'name': u'custom_metric',
                u'columns': [u'tagKey']
            }]
        }

        repo = influxdb_repo.MetricsRepository()

        result = repo.list_dimension_names(
            "38dc2a2549f94d2e9a4fa1cc45a4970c",
            "useast",
            "custom_metric")

        self.assertEqual(result,
                         [
                             {u'dimension_name': u'hostname'},
                             {u'dimension_name': u'service'}
                         ])

    @patch("monasca_api.common.repositories.influxdb."
           "metrics_repository.client.InfluxDBClient")
    def test_check_status(self, influxdb_client_mock):
        mock_client = influxdb_client_mock.return_value
        mock_client.request.return_value.status_code = 204

        repo = influxdb_repo.MetricsRepository()

        result = repo.check_status()

        self.assertEqual(result, (True, 'OK'))

    @patch("monasca_api.common.repositories.influxdb."
           "metrics_repository.client.InfluxDBClient")
    def test_check_status_server_error(self, influxdb_client_mock):
        mock_client = influxdb_client_mock.return_value
        mock_client.request.side_effect = \
            iexc.InfluxDBServerError('error')

        repo = influxdb_repo.MetricsRepository()

        result = repo.check_status()

        self.assertEqual(result, (False, 'error'))


class TestRepoMetricsCassandra(base.BaseTestCase):

    def setUp(self):
        super(TestRepoMetricsCassandra, self).setUp()
        self.conf_default(cluster_ip_addresses='127.0.0.1',
                          group='cassandra')

    @patch("monasca_api.common.repositories.cassandra."
           "metrics_repository.Cluster.connect")
    def test_list_metrics(self, cassandra_connect_mock):
        cassandra_session_mock = cassandra_connect_mock.return_value
        cassandra_session_mock.execute.return_value = [[
            "0b5e7d8c43f74430add94fba09ffd66e",
            "region",
            binascii.unhexlify(b"01d39f19798ed27bbf458300bf843edd17654614"),
            {
                "__name__": "disk.space_used_perc",
                "device": "rootfs",
                "hostname": "host0",
                "hosttype": "native",
                "mount_point": "/",
            }
        ]]

        repo = cassandra_repo.MetricsRepository()

        result = repo.list_metrics(
            "0b5e7d8c43f74430add94fba09ffd66e",
            "region",
            name="disk.space_user_perc",
            dimensions={
                "hostname": "host0",
                "hosttype": "native",
                "mount_point": "/",
                "device": "rootfs"},
            offset=None,
            limit=1)

        self.assertEqual([{
            u'id': u'01d39f19798ed27bbf458300bf843edd17654614',
            u'name': u'disk.space_used_perc',
            u'dimensions': {
                u'device': u'rootfs',
                u'hostname': u'host0',
                u'mount_point': u'/',
                u'hosttype': u'native'
            }}], result)

    @patch("monasca_api.common.repositories.cassandra."
           "metrics_repository.Cluster.connect")
    def test_list_metric_names(self, cassandra_connect_mock):

        Metric_map = namedtuple('Metric_map', 'metric_map')

        cassandra_session_mock = cassandra_connect_mock.return_value
        cassandra_session_mock.execute.return_value = [
            Metric_map(
                {
                    "__name__": "disk.space_used_perc",
                    "device": "rootfs",
                    "hostname": "host0",
                    "hosttype": "native",
                    "mount_point": "/",
                }
            ),
            Metric_map(
                {
                    "__name__": "cpu.idle_perc",
                    "hostname": "host0",
                    "service": "monitoring"
                }
            )
        ]

        repo = cassandra_repo.MetricsRepository()
        result = repo.list_metric_names(
            "0b5e7d8c43f74430add94fba09ffd66e",
            "region",
            dimensions={
                "hostname": "host0",
                "hosttype": "native",
                "mount_point": "/",
                "device": "rootfs"})

        self.assertEqual([
            {
                u'name': u'cpu.idle_perc'
            },
            {
                u'name': u'disk.space_used_perc'
            }
        ], result)

    @patch("monasca_api.common.repositories.cassandra."
           "metrics_repository.Cluster.connect")
    def test_measurement_list(self, cassandra_connect_mock):

        Measurement = namedtuple('Measurement', 'time_stamp value value_meta')

        cassandra_session_mock = cassandra_connect_mock.return_value
        cassandra_session_mock.execute.side_effect = [
            [[
                "0b5e7d8c43f74430add94fba09ffd66e",
                "region",
                binascii.unhexlify(b"01d39f19798ed27bbf458300bf843edd17654614"),
                {
                    "__name__": "disk.space_used_perc",
                    "device": "rootfs",
                    "hostname": "host0",
                    "hosttype": "native",
                    "mount_point": "/",
                    "service": "monitoring",
                }
            ]],
            [
                Measurement(self._convert_time_string("2015-03-14T09:26:53.59Z"), 2, None),
                Measurement(self._convert_time_string("2015-03-14T09:26:53.591Z"), 2.5, ''),
                Measurement(self._convert_time_string("2015-03-14T09:26:53.6Z"), 4.0, '{}'),
                Measurement(self._convert_time_string("2015-03-14T09:26:54Z"), 4,
                            '{"key": "value"}'),
            ]
        ]

        repo = cassandra_repo.MetricsRepository()
        result = repo.measurement_list(
            "tenant_id",
            "region",
            name="disk.space_used_perc",
            dimensions=None,
            start_timestamp=1,
            end_timestamp=2,
            offset=None,
            limit=1,
            merge_metrics_flag=True)

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]['dimensions'])
        self.assertEqual(result[0]['name'], 'disk.space_used_perc')
        self.assertEqual(result[0]['columns'],
                         ['timestamp', 'value', 'value_meta'])

        measurements = result[0]['measurements']

        self.assertEqual(
            [["2015-03-14T09:26:53.590Z", 2, {}],
             ["2015-03-14T09:26:53.591Z", 2.5, {}],
             ["2015-03-14T09:26:53.600Z", 4.0, {}],
             ["2015-03-14T09:26:54.000Z", 4, {"key": "value"}]],
            measurements
        )

    @patch("monasca_api.common.repositories.cassandra."
           "metrics_repository.Cluster.connect")
    def test_metrics_statistics(self, cassandra_connect_mock):

        Measurement = namedtuple('Measurement', 'time_stamp value value_meta')

        cassandra_session_mock = cassandra_connect_mock.return_value
        cassandra_session_mock.execute.side_effect = [
            [[
                "0b5e7d8c43f74430add94fba09ffd66e",
                "region",
                binascii.unhexlify(b"01d39f19798ed27bbf458300bf843edd17654614"),
                {
                    "__name__": "cpu.idle_perc",
                    "hostname": "host0",
                    "service": "monitoring",
                }
            ]],
            [
                Measurement(self._convert_time_string("2016-05-19T11:58:24Z"), 95.0, '{}'),
                Measurement(self._convert_time_string("2016-05-19T11:58:25Z"), 97.0, '{}'),
                Measurement(self._convert_time_string("2016-05-19T11:58:26Z"), 94.0, '{}'),
                Measurement(self._convert_time_string("2016-05-19T11:58:27Z"), 96.0, '{}'),
            ]
        ]

        start_timestamp = (self._convert_time_string("2016-05-19T11:58:24Z") -
                           datetime(1970, 1, 1)).total_seconds()
        end_timestamp = (self._convert_time_string("2016-05-19T11:58:27Z") -
                         datetime(1970, 1, 1)).total_seconds()
        print(start_timestamp)

        repo = cassandra_repo.MetricsRepository()
        result = repo.metrics_statistics(
            "tenant_id",
            "region",
            name="cpu.idle_perc",
            dimensions=None,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            statistics=['avg', 'min', 'max', 'count', 'sum'],
            period=300,
            offset=None,
            limit=1,
            merge_metrics_flag=True)

        self.assertEqual([
            {
                u'dimensions': None,
                u'statistics': [[u'2016-05-19T11:58:24Z', 95.5, 94, 97, 4, 382]],
                u'name': u'cpu.idle_perc',
                u'columns': [u'timestamp', u'avg', u'min', u'max', u'count', u'sum'],
                u'id': u'2016-05-19T11:58:24Z'
            }
        ], result)

    @patch("monasca_api.common.repositories.cassandra."
           "metrics_repository.Cluster.connect")
    def test_alarm_history(self, cassandra_connect_mock):

        AlarmHistory = namedtuple('AlarmHistory', 'alarm_id, time_stamp, metrics, '
                                                  'new_state, old_state, reason, '
                                                  'reason_data, sub_alarms, tenant_id')

        cassandra_session_mock = cassandra_connect_mock.return_value
        cassandra_session_mock.execute.return_value = [
            AlarmHistory('09c2f5e7-9245-4b7e-bce1-01ed64a3c63d',
                         self._convert_time_string("2016-05-19T11:58:27Z"),
                         """[{
                             "dimensions": {"hostname": "devstack", "service": "monitoring"},
                             "id": "",
                             "name": "cpu.idle_perc"
                         }]""",
                         'OK',
                         'UNDETERMINED',
                         'The alarm threshold(s) have not been exceeded for the sub-alarms: '
                         'avg(cpu.idle_perc) < 10.0 times 3 with the values: [84.35]',
                         '{}',
                         """[
                             {
                                 "sub_alarm_state": "OK",
                                 "currentValues": [
                                     "84.35"
                                 ],
                                 "sub_alarm_expression": {
                                     "function": "AVG",
                                     "period": 60,
                                     "threshold": 10.0,
                                     "periods": 3,
                                     "operator": "LT",
                                     "metric_definition": {
                                         "dimensions": "{}",
                                         "id": "",
                                         "name": "cpu.idle_perc"
                                     }
                                 }
                             }
                         ]""",
                         '741e1aa149524c0f9887a8d6750f67b1')
        ]

        repo = cassandra_repo.MetricsRepository()
        result = repo.alarm_history('741e1aa149524c0f9887a8d6750f67b1',
                                    ['09c2f5e7-9245-4b7e-bce1-01ed64a3c63d'],
                                    None, None)
        self.assertEqual(
            [{
                u'id': u'1463659107000',
                u'timestamp': u'2016-05-19T11:58:27.000Z',
                u'new_state': u'OK',
                u'old_state': u'UNDETERMINED',
                u'reason_data': u'{}',
                u'reason': u'The alarm threshold(s) have not been exceeded for the sub-alarms: '
                           u'avg(cpu.idle_perc) < 10.0 times 3 with the values: [84.35]',
                u'alarm_id': u'09c2f5e7-9245-4b7e-bce1-01ed64a3c63d',
                u'metrics': [{
                    u'id': u'',
                    u'name': u'cpu.idle_perc',
                    u'dimensions': {
                        u'service': u'monitoring',
                        u'hostname': u'devstack'
                    }
                }],
                u'sub_alarms': [
                    {
                        u'sub_alarm_state': u'OK',
                        u'currentValues': [
                            u'84.35'
                        ],
                        u'sub_alarm_expression': {
                            u'dimensions': u'{}',
                            u'threshold': 10.0,
                            u'periods': 3,
                            u'operator': u'LT',
                            u'period': 60,
                            u'metric_name': u'cpu.idle_perc',
                            u'function': u'AVG'
                        }
                    }
                ]
            }], result)

    @patch("monasca_api.common.repositories.cassandra."
           "metrics_repository.Cluster.connect")
    def test_check_status(self, _):
        repo = cassandra_repo.MetricsRepository()

        result = repo.check_status()

        self.assertEqual(result, (True, 'OK'))

    @patch("monasca_api.common.repositories.cassandra."
           "metrics_repository.Cluster.connect")
    def test_check_status_server_error(self, cassandra_connect_mock):
        repo = cassandra_repo.MetricsRepository()
        cassandra_connect_mock.side_effect = \
            cassandra.DriverException("Cluster is already shut down")

        result = repo.check_status()

        self.assertEqual(result, (False, 'Cluster is already shut down'))

    @staticmethod
    def _convert_time_string(date_time_string):
        dt = timeutils.parse_isotime(date_time_string)
        dt = timeutils.normalize_time(dt)
        return dt


def dummy_get_metrics(self, tenant_id, region,
                      start_timestamp=None, end_timestamp=None,
                      name=None):
    source = [
        ('0000000011111111',
         'process.cpu_perc',
         {'process_name': 'nova-api',
          'component': 'nova-api',
          'hostname': 'host0',
          'service': 'compute'},
         1505132600014),
        ('2222222233333333',
         'monasca.thread_count',
         {'component': 'monasca-agent',
          'hostname': 'host0',
          'service': 'monitoring'},
         1505132700014),
        ('4444444455555555',
         'process.cpu_perc',
         {'process_name': 'nova-api',
          'component': 'nova-api',
          'hostname': 'host1',
          'service': 'compute'},
         1505132600014),
        ('6666666677777777',
         'monasca.thread_count',
         {'component': 'monasca-agent',
          'hostname': 'host1',
          'service': 'monitoring'},
         1505132700014),
    ]
    if name:
        source = [_ for _ in source if _[1] == name]

    return {_[0]: griddb_repo.Metric(_[1], _[2]) for _ in source}


def dummy_get_measurements(self, tenant_id, region, metrics,
                           start_timestamp=None, end_timestamp=None):
    source = [
        (1505132600014, '0000000011111111', 50.0, ''),
        (1505132600014, '4444444455555555', 60.0, ''),
        (1505132700014, '2222222233333333', 10.0, ''),
        (1505132700014, '6666666677777777', 8.0, ''),
        (1505132800014, '0000000011111111', 40.0, ''),
        (1505132800014, '4444444455555555', 50.0, ''),
        (1505132900014, '2222222233333333', 8.0, ''),
        (1505132900014, '6666666677777777', 6.0, ''),
        (1505133000014, '0000000011111111', 30.0, ''),
        (1505133000014, '4444444455555555', 40.0, ''),
        (1505133100014, '2222222233333333', 6.0, ''),
        (1505133100014, '6666666677777777', 4.0, ''),
    ]
    if metrics:
        source = [_ for _ in source if _[1] in metrics]
    if start_timestamp:
        source = [_ for _ in source if _[0] >= start_timestamp * 1000]
    if end_timestamp:
        source = [_ for _ in source if _[0] <= end_timestamp * 1000]

    return [griddb_repo.Measurement(*_) for _ in source]


class TestRepoMetricsGridDB(base.BaseTestCase):
    @patch("monasca_api.common.repositories.griddb."
           "metrics_repository.griddb")
    def setUp(self, griddb_mock):
        super(TestRepoMetricsGridDB, self).setUp()
        self.repo = griddb_repo.MetricsRepository()

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    def test_list_metrics(self):
        result = self.repo.list_metrics(
            '0b5e7d8c43f74430add94fba09ffd66e',
            'region',
            name=None,
            dimensions={},
            offset=None,
            limit=None)

        self.assertEqual([{
            'id': '0000000011111111',
            'name': 'process.cpu_perc',
            'dimensions': {
                'process_name': 'nova-api',
                'component': 'nova-api',
                'hostname': 'host0',
                'service': 'compute'
            }}, {
            'id': '2222222233333333',
            'name': 'monasca.thread_count',
            'dimensions': {
                'component': 'monasca-agent',
                'hostname': 'host0',
                'service': 'monitoring'
            }}, {
            'id': '4444444455555555',
            'name': 'process.cpu_perc',
            'dimensions': {
                'process_name': 'nova-api',
                'component': 'nova-api',
                'hostname': 'host1',
                'service': 'compute'
            }}, {
            'id': '6666666677777777',
            'name': 'monasca.thread_count',
            'dimensions': {
                'component': 'monasca-agent',
                'hostname': 'host1',
                'service': 'monitoring'
            }}],
            result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    def test_list_metrics_with_limit(self):
        result = self.repo.list_metrics(
            '0b5e7d8c43f74430add94fba09ffd66e',
            'region',
            name=None,
            dimensions={},
            offset=None,
            limit=2)

        self.assertEqual([{
            'id': '0000000011111111',
            'name': 'process.cpu_perc',
            'dimensions': {
                'process_name': 'nova-api',
                'component': 'nova-api',
                'hostname': 'host0',
                'service': 'compute'
            }}, {
            'id': '2222222233333333',
            'name': 'monasca.thread_count',
            'dimensions': {
                'component': 'monasca-agent',
                'hostname': 'host0',
                'service': 'monitoring'
            }}],
            result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    def test_list_metrics_with_offset(self):
        result = self.repo.list_metrics(
            '0b5e7d8c43f74430add94fba09ffd66e',
            'region',
            name=None,
            dimensions={},
            offset='4444444455555555',
            limit=None)

        self.assertEqual([{
            'id': '4444444455555555',
            'name': 'process.cpu_perc',
            'dimensions': {
                'process_name': 'nova-api',
                'component': 'nova-api',
                'hostname': 'host1',
                'service': 'compute'
            }}, {
            'id': '6666666677777777',
            'name': 'monasca.thread_count',
            'dimensions': {
                'component': 'monasca-agent',
                'hostname': 'host1',
                'service': 'monitoring'
            }}],
            result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    def test_list_metrics_with_name(self):
        result = self.repo.list_metrics(
            '0b5e7d8c43f74430add94fba09ffd66e',
            'region',
            name='process.cpu_perc',
            dimensions={},
            offset=None,
            limit=None)

        self.assertEqual([{
            'id': '0000000011111111',
            'name': 'process.cpu_perc',
            'dimensions': {
                'process_name': 'nova-api',
                'component': 'nova-api',
                'hostname': 'host0',
                'service': 'compute'
            }}, {
            'id': '4444444455555555',
            'name': 'process.cpu_perc',
            'dimensions': {
                'process_name': 'nova-api',
                'component': 'nova-api',
                'hostname': 'host1',
                'service': 'compute'
            }}],
            result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    def test_list_metric_names(self):
        result = self.repo.list_metric_names(
            '0b5e7d8c43f74430add94fba09ffd66e',
            'region',
            dimensions={})

        self.assertEqual([
            {'name': 'monasca.thread_count'},
            {'name': 'process.cpu_perc'},
        ], result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    def test_list_metric_names_with_dimension(self):
        result = self.repo.list_metric_names(
            '0b5e7d8c43f74430add94fba09ffd66e',
            'region',
            dimensions={'service': 'compute'})

        self.assertEqual([
            {'name': 'process.cpu_perc'},
        ], result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    def test_list_dimension_names(self):
        result = self.repo.list_dimension_names(
            '0b5e7d8c43f74430add94fba09ffd66e',
            'region',
            'process.cpu_perc')

        self.assertEqual([
            {'dimension_name': 'process_name'},
            {'dimension_name': 'component'},
            {'dimension_name': 'hostname'},
            {'dimension_name': 'service'}
        ], result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    def test_list_dimension_values(self):
        result = self.repo.list_dimension_values(
            '0b5e7d8c43f74430add94fba09ffd66e',
            'region',
            'process.cpu_perc',
            'process_name')

        self.assertEqual([{'dimension_value': 'nova-api'}], result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_measurement_list(self):
        self.assertRaises(exceptions.RepositoryException,
                          self.repo.measurement_list,
                          'tenant_id',
                          'region',
                          name='process.cpu_perc',
                          dimensions=None,
                          start_timestamp=1505132600,
                          end_timestamp=None,
                          offset=None,
                          limit=None,
                          merge_metrics_flag=False,
                          group_by=None)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_measurement_list_with_dimension(self):
        dimensions = {
            'hostname': 'host0',
            'process_name': 'nova-api'
        }
        result = self.repo.measurement_list(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions=dimensions,
            start_timestamp=1505132600,
            end_timestamp=None,
            offset=None,
            limit=None,
            merge_metrics_flag=False,
            group_by=None)

        self.assertEqual([
            {
                u'columns': [u'timestamp', u'value', u'value_meta'],
                u'dimensions': dimensions,
                u'id': u'2017-09-11T12:30:00.014Z',
                u'measurements': [(u'2017-09-11T12:23:20.014Z', 50.0, ''),
                                  (u'2017-09-11T12:26:40.014Z', 40.0, ''),
                                  (u'2017-09-11T12:30:00.014Z', 30.0, '')],
                u'name': 'process.cpu_perc'
            }], result
        )

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_measurement_list_with_limit(self):
        dimensions = {
            'hostname': 'host0',
            'process_name': 'nova-api'
        }
        result = self.repo.measurement_list(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions=dimensions,
            start_timestamp=1505132600,
            end_timestamp=None,
            offset=None,
            limit=2,
            merge_metrics_flag=False,
            group_by=None)

        self.assertEqual([
            {
                u'columns': [u'timestamp', u'value', u'value_meta'],
                u'dimensions': dimensions,
                u'id': u'2017-09-11T12:26:40.014Z',
                u'measurements': [(u'2017-09-11T12:23:20.014Z', 50.0, ''),
                                  (u'2017-09-11T12:26:40.014Z', 40.0, '')],
                u'name': 'process.cpu_perc'
            }], result
        )

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_measurement_list_with_end_timestamp(self):
        dimensions = {
            'hostname': 'host0',
            'process_name': 'nova-api'
        }
        result = self.repo.measurement_list(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions=dimensions,
            start_timestamp=1505132600,
            end_timestamp=1505132800,
            offset=None,
            limit=None,
            merge_metrics_flag=False,
            group_by=None)

        self.assertEqual([
            {
                u'columns': [u'timestamp', u'value', u'value_meta'],
                u'dimensions': dimensions,
                u'id': u'2017-09-11T12:23:20.014Z',
                u'measurements': [(u'2017-09-11T12:23:20.014Z', 50.0, '')],
                u'name': 'process.cpu_perc'
            }], result
        )

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_measurement_list_with_offset(self):
        dimensions = {
            'hostname': 'host0',
            'process_name': 'nova-api'
        }
        result = self.repo.measurement_list(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions=dimensions,
            start_timestamp=1505132600,
            end_timestamp=None,
            offset=u'2017-09-11T12:26:40.014Z',
            limit=None,
            merge_metrics_flag=False,
            group_by=None)

        self.assertEqual([
            {
                u'columns': [u'timestamp', u'value', u'value_meta'],
                u'dimensions': dimensions,
                u'id': u'2017-09-11T12:30:00.014Z',
                u'measurements': [(u'2017-09-11T12:26:40.014Z', 40.0, ''),
                                  (u'2017-09-11T12:30:00.014Z', 30.0, '')],
                u'name': 'process.cpu_perc'
            }], result
        )

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_measurement_list_with_group_by(self):
        result = self.repo.measurement_list(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions={},
            start_timestamp=1505132600,
            end_timestamp=None,
            offset=None,
            limit=None,
            merge_metrics_flag=False,
            group_by=['hostname'])

        self.assertEqual([
            {
                u'columns': [u'timestamp', u'value', u'value_meta'],
                u'dimensions': {'hostname': 'host0'},
                u'id': u'2017-09-11T12:30:00.014Z',
                u'measurements': [(u'2017-09-11T12:23:20.014Z', 50.0, ''),
                                  (u'2017-09-11T12:26:40.014Z', 40.0, ''),
                                  (u'2017-09-11T12:30:00.014Z', 30.0, '')],
                u'name': 'process.cpu_perc'
            }, {
                u'columns': [u'timestamp', u'value', u'value_meta'],
                u'dimensions': {'hostname': 'host1'},
                u'id': u'2017-09-11T12:30:00.014Z',
                u'measurements': [(u'2017-09-11T12:23:20.014Z', 60.0, ''),
                                  (u'2017-09-11T12:26:40.014Z', 50.0, ''),
                                  (u'2017-09-11T12:30:00.014Z', 40.0, '')],
                u'name': 'process.cpu_perc'
            }], result
        )

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_measurement_list_with_merge_metrics(self):
        result = self.repo.measurement_list(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions=None,
            start_timestamp=1505132600,
            end_timestamp=None,
            offset=None,
            limit=None,
            merge_metrics_flag=True,
            group_by=None)

        self.assertEqual([
            {
                u'columns': [u'timestamp', u'value', u'value_meta'],
                u'dimensions': None,
                u'id': u'2017-09-11T12:30:00.014Z',
                u'measurements': [
                    (u'2017-09-11T12:23:20.014Z', 50.0, ''),
                    (u'2017-09-11T12:23:20.014Z', 60.0, ''),
                    (u'2017-09-11T12:26:40.014Z', 40.0, ''),
                    (u'2017-09-11T12:26:40.014Z', 50.0, ''),
                    (u'2017-09-11T12:30:00.014Z', 30.0, ''),
                    (u'2017-09-11T12:30:00.014Z', 40.0, '')],
                u'name': 'process.cpu_perc'
            }], result
        )

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_metrics_statistics(self):
        self.assertRaises(exceptions.RepositoryException,
                          self.repo.metrics_statistics,
                          'tenant_id',
                          'region',
                          name='process.cpu_perc',
                          dimensions=None,
                          start_timestamp=1505132600,
                          end_timestamp=None,
                          statistics=['avg', 'min', 'max', 'count', 'sum'],
                          period=300,
                          offset=None,
                          limit=None,
                          merge_metrics_flag=False,
                          group_by=None)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_metrics_statistics_with_dimensions(self):
        dimensions = {
            'hostname': 'host0',
            'process_name': 'nova-api'
        }
        result = self.repo.metrics_statistics(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions=dimensions,
            start_timestamp=1505132600,
            end_timestamp=None,
            statistics=['avg', 'min', 'max', 'count', 'sum'],
            period=300,
            offset=None,
            limit=None,
            merge_metrics_flag=False,
            group_by=None)

        self.assertEqual([
            {
                u'columns': [u'timestamp', u'avg', u'min', u'max', u'count',
                             u'sum'],
                u'dimensions': dimensions,
                u'id': u'2017-09-11T12:30:00.014Z',
                u'name': 'process.cpu_perc',
                u'statistics': [
                    [u'2017-09-11T12:23:20.014Z', 45.0, 40.0, 50.0, 2, 90.0],
                    [u'2017-09-11T12:30:00.014Z', 30.0, 30.0, 30.0, 1, 30.0]]
            }
        ], result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_metrics_statistics_with_large_period(self):
        dimensions = {
            'hostname': 'host0',
            'process_name': 'nova-api'
        }
        result = self.repo.metrics_statistics(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions=dimensions,
            start_timestamp=1505132600,
            end_timestamp=None,
            statistics=['avg', 'min', 'max', 'count', 'sum'],
            period=900,
            offset=None,
            limit=None,
            merge_metrics_flag=False,
            group_by=None)

        self.assertEqual([
            {
                u'columns': [u'timestamp', u'avg', u'min', u'max', u'count',
                             u'sum'],
                u'dimensions': dimensions,
                u'id': u'2017-09-11T12:23:20.014Z',
                u'name': 'process.cpu_perc',
                u'statistics': [
                    [u'2017-09-11T12:23:20.014Z', 40.0, 30.0, 50.0, 3, 120.0]]
            }
        ], result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_metrics_statistics_with_limit(self):
        dimensions = {
            'hostname': 'host0',
            'process_name': 'nova-api'
        }
        result = self.repo.metrics_statistics(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions=dimensions,
            start_timestamp=1505132600,
            end_timestamp=None,
            statistics=['avg', 'min', 'max', 'count', 'sum'],
            period=300,
            offset=None,
            limit=1,
            merge_metrics_flag=False,
            group_by=None)

        self.assertEqual([
            {
                u'columns': [u'timestamp', u'avg', u'min', u'max', u'count',
                             u'sum'],
                u'dimensions': dimensions,
                u'id': u'2017-09-11T12:23:20.014Z',
                u'name': 'process.cpu_perc',
                u'statistics': [
                    [u'2017-09-11T12:23:20.014Z', 45.0, 40.0, 50.0, 2, 90.0]],
            }
        ], result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_metrics_statistics_with_end_timestamp(self):
        dimensions = {
            'hostname': 'host0',
            'process_name': 'nova-api'
        }
        result = self.repo.metrics_statistics(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions=dimensions,
            start_timestamp=1505132600,
            end_timestamp=1505132800,
            statistics=['avg', 'min', 'max', 'count', 'sum'],
            period=300,
            offset=None,
            limit=None,
            merge_metrics_flag=False,
            group_by=None)

        self.assertEqual([
            {
                u'columns': [u'timestamp', u'avg', u'min', u'max', u'count',
                             u'sum'],
                u'dimensions': dimensions,
                u'id': u'2017-09-11T12:23:20.014Z',
                u'name': 'process.cpu_perc',
                u'statistics': [
                    [u'2017-09-11T12:23:20.014Z', 50.0, 50.0, 50.0, 1, 50.0]],
            }
        ], result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_metrics_statistics_with_offset(self):
        dimensions = {
            'hostname': 'host0',
            'process_name': 'nova-api'
        }
        result = self.repo.metrics_statistics(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions=dimensions,
            start_timestamp=1505132600,
            end_timestamp=None,
            statistics=['avg', 'min', 'max', 'count', 'sum'],
            period=300,
            offset=u'2017-09-11T12:26:40.014Z',
            limit=None,
            merge_metrics_flag=False,
            group_by=None)

        self.assertEqual([
            {
                u'columns': [u'timestamp', u'avg', u'min', u'max', u'count',
                             u'sum'],
                u'dimensions': dimensions,
                u'id': u'2017-09-11T12:26:40.014Z',
                u'name': 'process.cpu_perc',
                u'statistics': [
                    [u'2017-09-11T12:26:40.014Z', 35.0, 30.0, 40.0, 2, 70.0]]
            }
        ], result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_metrics_statistics_with_group_by(self):
        dimensions = {
            'process_name': 'nova-api'
        }
        result = self.repo.metrics_statistics(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions=dimensions,
            start_timestamp=1505132600,
            end_timestamp=None,
            statistics=['avg', 'min', 'max', 'count', 'sum'],
            period=300,
            offset=None,
            limit=None,
            merge_metrics_flag=False,
            group_by=['hostname'])

        self.assertEqual([
            {
                u'columns': [
                    u'timestamp', u'avg', u'min', u'max', u'count', u'sum'],
                u'dimensions': {'hostname': 'host0'},
                u'id': u'2017-09-11T12:30:00.014Z',
                u'name': 'process.cpu_perc',
                u'statistics': [
                    [u'2017-09-11T12:23:20.014Z', 45.0, 40.0, 50.0, 2, 90.0],
                    [u'2017-09-11T12:30:00.014Z', 30.0, 30.0, 30.0, 1, 30.0]
                ]
            }, {
                u'columns': [
                    u'timestamp', u'avg', u'min', u'max', u'count', u'sum'],
                u'dimensions': {'hostname': 'host1'},
                u'id': u'2017-09-11T12:30:00.014Z',
                u'name': 'process.cpu_perc',
                u'statistics': [
                    [u'2017-09-11T12:23:20.014Z', 55.0, 50.0, 60.0, 2, 110.0],
                    [u'2017-09-11T12:30:00.014Z', 40.0, 40.0, 40.0, 1, 40.0]
                ]
            }
        ], result)

    @patch.object(griddb_repo.MetricsRepository, '_get_metrics',
                  dummy_get_metrics)
    @patch.object(griddb_repo.MetricsRepository, '_get_measurements',
                  dummy_get_measurements)
    def test_metrics_statistics_with_merge_metrics(self):
        dimensions = {
            'process_name': 'nova-api'
        }
        result = self.repo.metrics_statistics(
            'tenant_id',
            'region',
            name='process.cpu_perc',
            dimensions=dimensions,
            start_timestamp=1505132600,
            end_timestamp=None,
            statistics=['avg', 'min', 'max', 'count', 'sum'],
            period=300,
            offset=u'2017-09-11T12:26:40.014Z',
            limit=None,
            merge_metrics_flag=True,
            group_by=None)

        self.assertEqual([
            {
                u'columns': [u'timestamp', u'avg', u'min', u'max', u'count',
                             u'sum'],
                u'dimensions': dimensions,
                u'id': u'2017-09-11T12:26:40.014Z',
                u'name': 'process.cpu_perc',
                u'statistics': [
                    [u'2017-09-11T12:26:40.014Z', 40.0, 30.0, 50.0, 4, 160.0]]
            }
        ], result)

    def test_alarm_history(self):

        self.repo._get_alarm_histories = mock.Mock()
        self.repo._get_alarm_histories.return_value = [
            griddb_repo.AlarmHistory(
                1505132600014,
                '09c2f5e7-9245-4b7e-bce1-01ed64a3c63d', [{
                    'id': '',
                    'name': 'process.cpu_perc',
                    'dimensions': {
                        'process_name': 'nova-api',
                        'component': 'nova-api',
                        'hostname': 'host0',
                        'service': 'compute'}}],
                'OK',
                'UNDETERMINED',
                'The alarm threshold(s) have not been exceeded for the sub-alarms: '
                'avg(cpu.idle_perc) < 10.0 times 3 with the values: [84.35]',
                [
                    {
                        'sub_alarm_state': 'OK',
                        'currentValues': [
                            '84.35'
                        ],
                        'sub_alarm_expression': {
                            'dimensions': {},
                            'threshold': 10.0,
                            'periods': 3,
                            'operator': 'LT',
                            'period': 60,
                            'function': 'AVG',
                            'metric_definition': {
                                'dimensions': {},
                                'id': '',
                                'name': 'process.cpu_perc',
                            }
                        }
                    }
                ],
                '0000000011111111')]

        result = self.repo.alarm_history('741e1aa149524c0f9887a8d6750f67b1',
                                         ['09c2f5e7-9245-4b7e-bce1-01ed64a3c63d'],
                                         None, None)
        self.assertEqual(
            [{
                'id': '0000000011111111',
                'timestamp': '2017-09-11T12:23:20.014Z',
                'new_state': 'OK',
                'old_state': 'UNDETERMINED',
                'reason_data': '{}',
                'reason': 'The alarm threshold(s) have not been exceeded for the sub-alarms: '
                          'avg(cpu.idle_perc) < 10.0 times 3 with the values: [84.35]',
                'alarm_id': '09c2f5e7-9245-4b7e-bce1-01ed64a3c63d',
                'metrics': [{
                    'id': '',
                    'name': 'process.cpu_perc',
                    'dimensions': {
                        'process_name': 'nova-api',
                        'component': 'nova-api',
                        'hostname': 'host0',
                        'service': 'compute'}}],
                'sub_alarms': [
                    {
                        'sub_alarm_state': 'OK',
                        'currentValues': [
                            '84.35'
                        ],
                        'sub_alarm_expression': {
                            'dimensions': {},
                            'metric_name': 'process.cpu_perc',
                            'threshold': 10.0,
                            'periods': 3,
                            'operator': 'LT',
                            'period': 60,
                            'function': 'AVG'
                        }
                    }
                ]
            }], result)

    def test_check_status(self):
        result = self.repo.check_status()

        self.assertEqual(result, (True, 'OK'))

    @patch("monasca_api.common.repositories.griddb."
           "metrics_repository.griddb.StoreFactory.get_default")
    def test_check_status_server_error(self, factory_mock):
        factory_mock.side_effect = griddb.GSException(140000)

        result = self.repo.check_status()

        self.assertEqual(result, (False, 'Error with number 140000'))
