# Copyright 2019 FUJITSU LIMITED
# Copyright 2018 OP5 AB
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import json

import falcon
import fixtures
import oslo_config.fixture

from monasca_api.tests import base
from monasca_api.v2.reference import metrics


CONF = oslo_config.cfg.CONF

TENANT_ID = u"fedcba9876543210fedcba9876543210"


class MetricsTest(base.BaseApiTestCase):
    def setUp(self):
        super(MetricsTest, self).setUp()

        self.useFixture(fixtures.MockPatch(
            'monasca_api.common.messaging.kafka_publisher.KafkaPublisher'
        ))
        self.metrics_repo_mock = self.useFixture(fixtures.MockPatch(
            'monasca_api.common.repositories.influxdb.metrics_repository.MetricsRepository'
        )).mock

        # [messaging]
        self.conf_override(
            driver='monasca_api.common.messaging.'
                   'kafka_publisher:KafkaPublisher',
            group='messaging')

        self.metrics_resource = metrics.Metrics()

        self.api.add_route('/v2.0/metrics',
                           self.metrics_resource)

    def test_list_metrics(self):
        expected_elements = \
            {'elements': [{'id': '0',
                           'name': 'cpu.utilization',
                           'dimensions':
                               {'hostname': 'host0',
                                'db': 'vegeta'}},
                          {'id': '1',
                           'name': 'cpu.idle_perc',
                           'dimensions':
                               {'hostname': 'host0',
                                'db': 'vegeta'}}
                          ]}

        return_value = self.metrics_repo_mock.return_value
        return_value.list_metrics.return_value = expected_elements['elements']

        response = self.simulate_request('/v2.0/metrics',
                                         headers={'X-Roles':
                                                  CONF.security.default_authorized_roles[0],
                                                  'X-Tenant-Id': TENANT_ID},
                                         method='GET')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, base.RESTResponseEquals(expected_elements))

    def test_send_metrics(self):
        request_body = {
            "name": "cpu.idle_perc",
            "dimensions": {
                "hostname": "host0",
                "db": "vegeta"
            },
            "timestamp": 1405630174123,
            "value": 1.0,
            "value_meta": {
                "key1": "value1",
                "key2": "value2"
            }}
        self.simulate_request('/v2.0/metrics',
                              headers={'X-Roles':
                                           CONF.security.default_authorized_roles[0],
                                       'X-Tenant-Id': TENANT_ID,
                                       'Content-Type': 'application/json'},
                              body=json.dumps(request_body),
                              method='POST')
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    def test_send_metric(self):
        request_body = {
            "name": "cpu.idle_perc",
            "dimensions": {
                "hostname": "host0",
                "db": "vegeta"
            },
            "timestamp": 1405630174123,
            "value": 1.0}
        self.simulate_request('/v2.0/metrics',
                              headers={'X-Roles':
                                       CONF.security.default_authorized_roles[0],
                                       'X-Tenant-Id': TENANT_ID,
                                       'Content-Type': 'application/json'},
                              body=json.dumps(request_body),
                              method='POST')
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    def test_send_incorrect_metric(self):
        request_body = {
            "name": "cpu.idle_perc",
            "dimensions": 'oh no',
            "timestamp": 1405630174123,
            "value": 1.0}
        self.simulate_request('/v2.0/metrics',
                              headers={'X-Roles':
                                       CONF.security.default_authorized_roles[0],
                                       'X-Tenant-Id': TENANT_ID,
                                       'Content-Type': 'application/json'},
                              body=json.dumps(request_body),
                              method='POST')
        self.assertEqual(falcon.HTTP_422, self.srmock.status)