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
from monasca_api.v2.reference import group_rules

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
            'group_rules_driver',
            'monasca_api.common.repositories.group_rules_repository:GroupRulesRepository',
            group='repositories', enforce_type=True)


class AlarmTestBase(falcon.testing.TestBase, oslotest.BaseTestCase):

    api_class = base.MockedAPI

    def setUp(self):
        super(AlarmTestBase, self).setUp()

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


class GroupRuleTestBase(AlarmTestBase):

    def setUp(self):
        super(GroupRuleTestBase, self).setUp()

        self.group_rule_repo_mock = self.useFixture(fixtures.MockPatch(
            'monasca_api.common.repositories.group_rules_repository.GroupRulesRepository'
        )).mock

        self.group_rule_resource = group_rules.GroupRules()
        self.group_rule_resource.send_event = Mock()
        self._send_event = self.group_rule_resource.send_event

        self.api.add_route("/v2.0/group-rules/",
                           self.group_rule_resource)
        self.api.add_route("/v2.0/group-rules/{group_rule_id}",
                           self.group_rule_resource)

        self.trap = []

    def test_group_rule_create(self):
        return_value = self.group_rule_repo_mock.return_value
        return_value.get_group_rules.return_value = []
        return_value.create_group_rule.return_value = \
            u"00000001-0001-0001-0001-000000000001"

        group_rule = {
            "name": "test_group_rule",
            "expression": "group by hostname, service"
        }

        expected_data = {
            u"name": u"test_group_rule",
            u"description": u'',
            u"expression": u'group by hostname, service',
            u"group_wait": u"30s",
            u"repeat_interval": u"2h",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'alarm_actions': [],
            u'ok_actions': [],
            u'undetermined_actions': []
        }

        response = self.simulate_request("/v2.0/group-rules/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(group_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

        ((_, event), _) = self._send_event.call_args
        fields = {u"name": u"test_group_rule",
                  u'tenantId': TENANT_ID,
                  u'matchers': ['hostname', 'service'],
                  u'exclusions': {},
                  u"group_wait": u"30s",
                  u"repeat_interval": u"2h",
                  u"id": u"00000001-0001-0001-0001-000000000001",
                  u'alarm_actions': [],
                  u'ok_actions': [],
                  u'undetermined_actions': []
                  }
        reference = {u'group-rule-created': fields}
        self.assertEqual(reference, event)

    def test_group_rule_create_with_optional_params(self):
        return_value = self.group_rule_repo_mock.return_value
        return_value.get_group_rules.return_value = []
        return_value.create_group_rule.return_value = \
            u"00000001-0001-0001-0001-000000000001"

        group_rule = {
            "name": "test_group_rule",
            "description": "Test Group Rule",
            "expression": "group by hostname, service",
            "group_wait": "2m",
            "repeat_interval": "60s"
        }

        expected_data = {
            u"name": u"test_group_rule",
            u"description": u"Test Group Rule",
            u"expression": u'group by hostname, service',
            u"group_wait": u"2m",
            u"repeat_interval": u"60s",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'alarm_actions': [],
            u'ok_actions': [],
            u'undetermined_actions': []
        }

        response = self.simulate_request("/v2.0/group-rules/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(group_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_group_rule_create_with_unique_actions(self):
        return_value = self.group_rule_repo_mock.return_value
        return_value.get_group_rules.return_value = []
        return_value.create_group_rule.return_value = \
            u"00000001-0001-0001-0001-000000000001"

        group_rule = {
            "name": "test_group_rule",
            "expression": "group by hostname, service",
            "alarm_actions": ["abc123"],
            "ok_actions": ["bcd234"],
            "undetermined_actions": ["cde345"]
        }

        expected_data = {
            u"name": u"test_group_rule",
            u"description": '',
            u"expression": u'group by hostname, service',
            u"group_wait": u"30s",
            u"repeat_interval": u"2h",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'alarm_actions': [u"abc123"],
            u'ok_actions': [u"bcd234"],
            u'undetermined_actions': [u"cde345"]
        }

        response = self.simulate_request("/v2.0/group-rules/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(group_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_group_rule_create_with_same_actions(self):
        return_value = self.group_rule_repo_mock.return_value
        return_value.get_group_rules.return_value = []
        return_value.create_group_rule.return_value = \
            u"00000001-0001-0001-0001-000000000001"

        group_rule = {
            "name": "test_group_rule",
            "expression": "group by hostname, service",
            "alarm_actions": ["abc123"],
            "ok_actions": ["abc123"],
            "undetermined_actions": ["abc123"]
        }

        expected_data = {
            u"name": u"test_group_rule",
            u"description": '',
            u"expression": u'group by hostname, service',
            u"group_wait": u"30s",
            u"repeat_interval": u"2h",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'alarm_actions': [u"abc123"],
            u'ok_actions': [u"abc123"],
            u'undetermined_actions': [u"abc123"]
        }

        response = self.simulate_request("/v2.0/group-rules/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(group_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_group_rule_create_with_similar_name(self):
        return_value = self.group_rule_repo_mock.return_value
        return_value.get_group_rules.return_value = [u"abc123"]
        return_value.create_group_rule.return_value = \
            u"00000001-0001-0001-0001-000000000001"

        group_rule = {
            "name": "test_group_rule",
            "expression": "group by hostname, service"
        }

        self.simulate_request("/v2.0/group-rules/",
                              headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                              method="POST",
                              body=json.dumps(group_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_409,
                         u"should have failed due to existing similar name")

    def test_group_rule_create_without_required_fields(self):
        return_value = self.group_rule_repo_mock.return_value
        return_value.get_group_rules.return_value = [u"abc123"]
        return_value.create_group_rule.return_value = \
            u"00000001-0001-0001-0001-000000000001"

        group_rule = {
            "name": "test_group_rule",
            "expression": "group by hostname, service"
        }

        for key, value in group_rule.items():
            self.simulate_request("/v2.0/group-rules/",
                                  headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                  method="POST",
                                  body=json.dumps({key: value}))

            self.assertEqual(self.srmock.status, falcon.HTTP_422,
                             u"should have failed because required field {} "
                             u"was missing".format(value))

    def test_group_rule_update(self):
        self.group_rule_repo_mock.return_value.get_group_rules.return_value = []
        self.group_rule_repo_mock.return_value.update_or_patch_group_rule.return_value = (
            {u'alarm_actions': u"123abc",
             u'ok_actions': u"123abc",
             u'id': u'00000001-0001-0001-0001-000000000001',
             u'name': u'Test Alarm',
             u'description': u'test group rule',
             u'undetermined_actions': u"123abc",
             u"expression": u'group by hostname, service',
             u'group_wait': u'30s',
             u'repeat_interval': u'2h'
             }
        )

        expected_rule = {
            u'id': u'00000001-0001-0001-0001-000000000001',
            u'alarm_actions': [u"123abc"],
            u'ok_actions': [u"123abc"],
            u'links': [{u'href': u'http://falconframework.org/v2.0/group-rules/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': u'Test Alarm',
            u'description': u'test group rule',
            u'undetermined_actions': [u"123abc"],
            u"expression": u'group by hostname, service',
            u'group_wait': u'30s',
            u'repeat_interval': u'2h'
        }

        group_rule = {
            "name": "test_group_rule",
            "description": "test group rule",
            "expression": "group by hostname, service",
            "group_wait": "30s",
            "repeat_interval": "2h",
            'alarm_actions': ["123abc"],
            'ok_actions': ["123abc"],
            'undetermined_actions': ["123abc"]
        }

        result = self.simulate_request("/v2.0/group-rules/%s" % expected_rule[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                       method="PUT",
                                       body=json.dumps(group_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_rule = json.loads(result[0])
        self.assertEqual(result_rule, expected_rule)

    def test_group_rule_update_missing_fields(self):
        self.group_rule_repo_mock.return_value.get_group_rules.return_value = []
        self.group_rule_repo_mock.return_value.update_or_patch_group_rule.return_value = (
            {u'alarm_actions': [],
             u'ok_actions': [],
             u'id': u'00000001-0001-0001-0001-000000000001',
             u'name': u'test_group_rule_missing_fields',
             u'description': u'test group rule update with missing fields',
             u'undetermined_actions': [],
             u"expression": u'group by hostname, service',
             u'group_wait': u'30s',
             u'repeat_interval': u'2h'
             }
        )

        expected_def = {
            u'id': u'00000001-0001-0001-0001-000000000001',
            u'alarm_actions': [],
            u'ok_actions': [],
            u'links': [{u'href': u'http://falconframework.org/v2.0/group-rules/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': u'test_group_rule_missing_fields',
            u'description': u'test group rule update with missing fields',
            u'undetermined_actions': [],
            u"expression": u'group by hostname, service',
            u'group_wait': u'30s',
            u'repeat_interval': u'2h'
        }

        group_rule = {
            "name": "test_group_rule_missing_fields",
            "expression": "group by hostname, service",
            "group_wait": "30s",
            "repeat_interval": "2h",
            "description": "test group rule update with missing fields",
            'alarm_actions': [],
            'ok_actions': [],
            'undetermined_actions': []
        }
        result = self.simulate_request("/v2.0/group-rules/%s" % expected_def[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                       method="PUT",
                                       body=json.dumps(group_rule))
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(result[0])
        self.assertEqual(result_def, expected_def)

        for key, value in group_rule.iteritems():
            del group_rule[key]
            self.simulate_request("/v2.0/group-rules/%s" % expected_def[u'id'],
                                  headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                  method="PUT",
                                  body=json.dumps(group_rule))
            self.assertEqual(self.srmock.status, "422 Unprocessable Entity",
                             u"should have failed without key {}".format(key))
            group_rule[key] = value

    def test_group_rule_patch(self):
        self.group_rule_repo_mock.return_value.get_group_rules.return_value = []
        new_name = u'test_group_rule_updated'
        group_rule_def_id = u'00000001-0001-0001-0001-000000000001'
        expression = u'group by hostname, service'
        group_wait = u"1m"
        repeat_interval = u"30s"
        self.group_rule_repo_mock.return_value.update_or_patch_group_rule.return_value = (
            {u'alarm_actions': [],
             u'ok_actions': [],
             u'id': group_rule_def_id,
             u'name': new_name,
             u'description': u'test group rule patch',
             u'undetermined_actions': [],
             u'expression': u'group by hostname, service',
             u'group_wait': group_wait,
             u'repeat_interval': repeat_interval
             }
        )

        expected_rule = {
            u'id': group_rule_def_id,
            u'alarm_actions': [],
            u'ok_actions': [],
            u'links': [{u'href': u'http://falconframework.org/v2.0/group-rules/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': new_name,
            u'description': u'test group rule patch',
            u'undetermined_actions': [],
            u'expression': expression,
            u'group_wait': group_wait,
            u'repeat_interval': repeat_interval
        }

        group_rule = {
            u'name': new_name,
            u'expression': expression
        }

        result = self.simulate_request("/v2.0/group-rules/%s" % expected_rule[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                       method="PATCH",
                                       body=json.dumps(group_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(result[0])
        self.assertEqual(result_def, expected_rule)

        ((_, event), _) = self._send_event.call_args
        fields = {u'alarm_actions': None,
                  u'ok_actions': None,
                  u'id': group_rule_def_id,
                  u'name': new_name,
                  u'description': u'test group rule patch',
                  u'undetermined_actions': None,
                  u'matchers': ['hostname', 'service'],
                  u'exclusions': {},
                  u'group_wait': group_wait,
                  u'tenantId': TENANT_ID,
                  u'repeat_interval': repeat_interval
                  }
        reference = {u'group-rule-updated': fields}
        self.assertEqual(reference, event)

    def test_group_rule_get_specific_rule(self):
        self.group_rule_repo_mock.return_value.get_group_rule.return_value = {
            u'alarm_actions': None,
            u'ok_actions': None,
            u'id': u'00000001-0001-0001-0001-000000000001',
            u'name': u'test_get_group_rule',
            u'description': u'test get group rule',
            u'undetermined_actions': None,
            u'expression': u'group by hostname, service',
            u'group_wait': u'30s',
            u'repeat_interval': u'2h'
        }

        expected_data = {
            u'alarm_actions': [],
            u'ok_actions': [],
            u'id': u'00000001-0001-0001-0001-000000000001',
            u'name': u'test_get_group_rule',
            u'description': 'test get group rule',
            u'undetermined_actions': [],
            u'expression': u'group by hostname, service',
            u'group_wait': u'30s',
            u'repeat_interval': u'2h'
        }

        response = self.simulate_request(
            '/v2.0/group-rules/%s' % (expected_data[u'id']),
            headers={
                'X-Roles': 'admin',
                'X-Tenant-Id': TENANT_ID,
            })

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_get_alarm_definitions_with_multibyte_character(self):
        rule_name = 'ａｌａｒｍ＿ｄｅｆｉｎｉｔｉｏｎ'
        if six.PY2:
            rule_name = rule_name.decode('utf8')
        self.group_rule_repo_mock.return_value.get_group_rule.return_value = {
            u'alarm_actions': None,
            u'ok_actions': None,
            u'id': u'00000001-0001-0001-0001-000000000001',
            u'name': rule_name,
            u'description': 'test_group_rule',
            u'undetermined_actions': None,
            u'expression': u'group by hostname, service',
            u'group_wait': u'30s',
            u'repeat_interval': u'2h'
        }

        expected_data = {
            u'alarm_actions': [],
            u'ok_actions': [],
            u'id': u'00000001-0001-0001-0001-000000000001',
            u'name': rule_name,
            u'description': 'test_group_rule',
            u'undetermined_actions': [],
            u'expression': u'group by hostname, service',
            u'group_wait': u'30s',
            u'repeat_interval': u'2h'
        }

        response = self.simulate_request(
            '/v2.0/group-rules/%s' % (expected_data[u'id']),
            headers={
                'X-Roles': 'admin',
                'X-Tenant-Id': TENANT_ID,
            })

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, RESTResponseEquals(expected_data))
