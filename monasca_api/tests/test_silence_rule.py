# -*- coding: utf-8 -*-
# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
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

import ujson as json

import falcon.testing
import fixtures
import testtools.matchers as matchers

from mock import Mock

from monasca_api.tests import base
from monasca_api.v2.reference import silence_rules

import oslo_config.fixture
import oslotest.base as oslotest
import six


CONF = oslo_config.cfg.CONF


TENANT_ID = u"ecacba9876543210fedcba9876543210"


class MonascaApiConfigFixture(oslo_config.fixture.Config):

    def setUp(self):
        super(MonascaApiConfigFixture, self).setUp()

        # [messaging]
        self.conf.set_override(
            'driver',
            'monasca_api.common.messaging.kafka_publisher:KafkaPublisher',
            group='messaging', enforce_type=True)

        # [repositories]
        self.conf.set_override(
            'silence_rules_driver',
            'monasca_api.common.repositories.silence_rules_repository:SilenceRulesRepository',
            group='repositories', enforce_type=True)


class TestBase(falcon.testing.TestBase, oslotest.BaseTestCase):

    api_class = base.MockedAPI

    def setUp(self):
        super(TestBase, self).setUp()

        self.useFixture(fixtures.MockPatch(
            'monasca_api.common.messaging.kafka_publisher.KafkaPublisher'))

        self.CONF = self.useFixture(MonascaApiConfigFixture(CONF)).conf


class RESTResponseEquals(object):
    """Match if the supplied data contains a single string containing a JSON
    object which decodes to match expected_data, excluding the contents of
    the 'links' key.
    """

    def __init__(self, expected_data):
        self.expected_data = expected_data

        if u"links" in expected_data:
            del expected_data[u"links"]

    def __str__(self):
        return 'RESTResponseEquals(%s)' % (self.expected,)

    def match(self, actual):
        if len(actual) != 1:
            return matchers.Mismatch("Response contains <> 1 item: %r" % actual)

        response_data = json.loads(actual[0])

        if u"links" in response_data:
            del response_data[u"links"]

        return matchers.Equals(self.expected_data).match(response_data)


class SilenceRuleTestBase(TestBase):

    def setUp(self):
        super(SilenceRuleTestBase, self).setUp()

        self.silence_rule_repo_mock = self.useFixture(fixtures.MockPatch(
            'monasca_api.common.repositories.silence_rules_repository.SilenceRulesRepository'
        )).mock

        self.silence_rule_resource = silence_rules.SilenceRules()
        self.silence_rule_resource.send_event = Mock()
        self._send_event = self.silence_rule_resource.send_event

        self.api.add_route("/v2.0/silence-rules/",
                           self.silence_rule_resource)
        self.api.add_route("/v2.0/silence-rules/{silence_rule_id}",
                           self.silence_rule_resource)

        self.trap = []

    def test_silence_rule_definition_create(self):
        return_value = self.silence_rule_repo_mock.return_value
        return_value.get_silence_rules.return_value = []
        return_value.create_silence_rule.return_value = u"00000001-0001-0001-0001-000000000001"

        silence_rule = {
            "name": "test_silence_rule",
            "expression": "targets cpu.percent",
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        expected_data = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"expression": u"targets cpu.percent",
            u"name": u"test_silence_rule",
            u"description": u"",
            u"silence_duration": u"10m",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/silence-rules/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(silence_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

        ((_, event), _) = self._send_event.call_args
        fields = {u"id": u"00000001-0001-0001-0001-000000000001",
                  u'tenantId': TENANT_ID,
                  u'matchers': {'__metricName__': 'cpu.percent'},
                  u"name": u"test_silence_rule",
                  u"silence_duration": u"10m",
                  u"start_time": u"2017-04-10T10:42:10.685Z"
                  }
        reference = {u'silence-rule-created': fields}
        self.assertEqual(reference, event)

    def test_silence_rule_definition_create_with_optional_params(self):
        return_value = self.silence_rule_repo_mock.return_value
        return_value.get_silence_rules.return_value = []
        return_value.create_silence_rule.return_value = u"00000001-0001-0001-0001-000000000001"

        silence_rule = {
            "name": "test_silence_rule",
            "description": "test silence rule",
            "expression": "targets cpu.percent",
            "silence_duration": "1d2h",
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        expected_data = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"expression": u"targets cpu.percent",
            u"name": u"test_silence_rule",
            u"description": u"test silence rule",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/silence-rules/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(silence_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_silence_rule_definition_create_with_same_name(self):
        return_value = self.silence_rule_repo_mock.return_value
        return_value.get_silence_rules.return_value = ["123abc"]
        return_value.create_silence_rule.return_value = u"00000001-0001-0001-0001-000000000001"

        silence_rule = {
            "name": "test_silence_rule",
            "expression": "targets cpu.percent",
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        self.simulate_request("/v2.0/silence-rules/",
                              headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                              method="POST",
                              body=json.dumps(silence_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_409,
                         u"Should have failed due to existing same name")

    def test_silence_rule_definition_create_without_required_fields(self):
        return_value = self.silence_rule_repo_mock.return_value
        return_value.get_silence_rules.return_value = []
        return_value.create_silence_rule.return_value = u"00000001-0001-0001-0001-000000000001"

        silence_rule = {
            "expression": {"alarmName": "test.AlarmName"},
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        self.simulate_request("/v2.0/silence-rules/",
                              headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                              method="POST",
                              body=json.dumps(silence_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_422,
                         "should have failed becasue required field name was "
                         "missing")

        silence_rule = {
            "name": "test_silence_rule",
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        self.simulate_request("/v2.0/silence-rules/",
                              headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                              method="POST",
                              body=json.dumps(silence_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_422,
                         "should have failed becasue required field expression"
                         " was missing")

    def test_silence_rule_definition_update(self):
        self.silence_rule_repo_mock.return_value.get_silence_rules.return_value = []
        self.silence_rule_repo_mock.return_value.update_or_patch_silence_rule.return_value = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"name": u"test_silence_rule",
            u"expression": u"targets cpu.percent",
            u"description": u"Updated silence rule",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        silence_rule = {
            "name": "test_silence_rule",
            "expression": "targets cpu.percent",
            "description": "Updated silence rule",
            "silence_duration": "1d2h",
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        expected_rule = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'links': [{u'href': u'http://falconframework.org/v2.0/silence-rules/'
                                 u'00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u"expression": u"targets cpu.percent",
            u"name": u"test_silence_rule",
            u"description": u"Updated silence rule",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/silence-rules/%s" % expected_rule[u'id'],
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="PUT",
                                         body=json.dumps(silence_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(response[0])
        self.assertEqual(result_def, expected_rule)

    def test_silence_rule_update_missing_fields(self):
        self.silence_rule_repo_mock.return_value.get_silence_rules.return_value = []
        self.silence_rule_repo_mock.return_value.update_or_patch_silence_rule.return_value = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"expression": u"targets cpu.percent",
            u"name": u"test_silence_rule",
            u"description": u"Updated silence rule",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        silence_rule = {
            "name": "test_silence_rule",
            "expression": "targets cpu.percent",
            "description": "Updated silence rule",
            "silence_duration": "1d2h",
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        expected_rule = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'links': [{u'href': u'http://falconframework.org/v2.0/silence-rules/'
                                 u'00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u"expression": u"targets cpu.percent",
            u"name": u"test_silence_rule",
            u"description": u"Updated silence rule",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/silence-rules/%s" % expected_rule[u'id'],
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="PUT",
                                         body=json.dumps(silence_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(response[0])
        self.assertEqual(result_def, expected_rule)

        for key, value in silence_rule.iteritems():
            del silence_rule[key]
            self.simulate_request("/v2.0/silence-rules/%s" % expected_rule[u'id'],
                                  headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                  method="PUT",
                                  body=json.dumps(silence_rule))
            self.assertEqual(self.srmock.status, "422 Unprocessable Entity",
                             u"should have failed without key {}".format(key))
            silence_rule[key] = value

    def test_silence_rule_update_no_id(self):
        silence_rule = {
            "name": "test_silence_rule_update_no_id",
            "expression": "targets cpu.percent",
            "description": "Updated silence rule with no id",
            "silence_duration": "1d2h",
            "start_time": "2017-04-10T10:42:10.685Z"
        }
        self.simulate_request("/v2.0/silence-rules",
                              headers={'X-Roles': 'admin',
                                       'X-Tenant-Id': TENANT_ID},
                              method="PUT",
                              body=json.dumps(silence_rule))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_silence_rule_definition_patch(self):
        self.silence_rule_repo_mock.return_value.get_silence_rules.return_value = []
        self.silence_rule_repo_mock.return_value.update_or_patch_silence_rule.return_value = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"expression": u"targets cpu.percent",
            u"name": u"test_silence_rule_patch",
            u"description": u"test silence rule patch",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        silence_rule = {
            "name": "test_silence_rule_patch",
        }

        expected_rule = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'links': [{u'href': u'http://falconframework.org/v2.0/silence-rules/'
                                 u'00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u"expression": u"targets cpu.percent",
            u"name": u"test_silence_rule_patch",
            u"description": u"test silence rule patch",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/silence-rules/%s" % expected_rule[u'id'],
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="PATCH",
                                         body=json.dumps(silence_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(response[0])
        self.assertEqual(result_def, expected_rule)

        ((_, event), _) = self._send_event.call_args
        fields = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"matchers": {'__metricName__': 'cpu.percent'},
            u"name": u"test_silence_rule_patch",
            u"description": u"test silence rule patch",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z",
            u'tenantId': TENANT_ID
        }
        reference = {u'silence-rule-updated': fields}
        self.assertEqual(reference, event)

    def test_silence_rule_patch_no_id(self):
        silence_rule = {
            "name": "test_silence_rule_patch_no_id",
            "expression": "targets cpu.percent"
        }
        self.simulate_request("/v2.0/silence-rules",
                              headers={'X-Roles': 'admin',
                                       'X-Tenant-Id': TENANT_ID},
                              method="PATCH",
                              body=json.dumps(silence_rule))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_silence_rule_delete_no_id(self):
        self.simulate_request("/v2.0/silence-rules",
                              headers={'X-Roles': 'admin',
                                       'X-Tenant-Id': TENANT_ID},
                              method="DELETE")
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_silence_rule_definition_get_specific_rule(self):
        self.silence_rule_repo_mock.return_value.get_silence_rule.return_value = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"expression": u"targets cpu.percent",
            u"name": u"test_silence_rule",
            u"description": u"test silence rule get",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        expected_rule = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'links': [{u'href': u'http://falconframework.org/v2.0/silence-rules/'
                                 u'00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u"expression": u"targets cpu.percent",
            u"name": u"test_silence_rule",
            u"description": u"test silence rule get",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/silence-rules/%s" % expected_rule[u'id'],
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID})

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, RESTResponseEquals(expected_rule))

    def test_silence_rule_definition_get_specific_rule_with_multibyte_character(self):
        rule_name = 'ａｌａｒｍ＿ｄｅｆｉｎｉｔｉｏｎ'
        if six.PY2:
            rule_name = rule_name.decode('utf8')
        self.silence_rule_repo_mock.return_value.get_silence_rule.return_value = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"expression": u"targets cpu.percent",
            u"name": rule_name,
            u"description": u"test silence rule get",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        expected_rule = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'links': [{u'href': u'http://falconframework.org/v2.0/silence-rules/'
                                 u'00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u"expression": u"targets cpu.percent",
            u"name": rule_name,
            u"description": u"test silence rule get",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/silence-rules/%s" % expected_rule[u'id'],
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID})

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, RESTResponseEquals(expected_rule))
