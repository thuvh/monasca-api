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

from collections import OrderedDict
import copy
import json

import falcon.testing
import fixtures
import testtools.matchers as matchers

from mock import Mock
from mock import patch

from monasca_api.tests import base
from monasca_api.v2.reference import alarm_group_definitions

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
            'alarm_group_definitions_driver',
            'monasca_api.common.repositories.alarm_group_definitions_repository:AlarmGroupDefinitionsRepository',
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


class GroupRuleDefinitionTestBase(AlarmTestBase):

    def setUp(self):
        super(GroupRuleDefinitionTestBase, self).setUp()

        self.group_def_repo_mock = self.useFixture(fixtures.MockPatch(
            'monasca_api.common.repositories.alarm_group_definitions_repository.AlarmGroupDefinitionsRepository'
        )).mock

        self.group_definition_resource = alarm_group_definitions.AlarmGroupDefinitions()
        self.group_definition_resource.send_event = Mock()
        self._send_event = self.group_definition_resource.send_event

        self.api.add_route("/v2.0/alarm-group-definitions/",
                           self.group_definition_resource)
        self.api.add_route("/v2.0/alarm-group-definitions/{alarm_group_definition_id}",
                           self.group_definition_resource)

        self.trap = []

    def test_group_rule_definition_create(self):
        return_value = self.group_def_repo_mock.return_value
        return_value.get_alarm_group_definitions.return_value = []
        return_value.create_alarm_group_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        group_def = {
            "name": "Test Definition",
            "matchers": ["alarmName", "metricName"]
        }

        expected_data = {
            u"name": u"Test Definition",
            u"matchers": [u"alarmName", u"metricName"],
            u"exclusions": [],
            u"group_wait": u"30s",
            u"repeat_interval": "2h",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'alarm_actions': [],
            u'ok_actions': [],
            u'undetermined_actions': []
        }

        response = self.simulate_request("/v2.0/alarm-group-definitions/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(group_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_group_rule_definition_create_with_optional_params(self):
        return_value = self.group_def_repo_mock.return_value
        return_value.get_alarm_group_definitions.return_value = []
        return_value.create_alarm_group_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        group_def = {
            "name": "Test Definition",
            "matchers": ["alarmName", "metricName"],
            "exclusions": {"alarmName": "test.alarmName"},
            "group_wait": "2m",
            "repeat_interval": "60s"
        }

        expected_data = {
            u"name": u"Test Definition",
            u"matchers": [u"alarmName", u"metricName"],
            u"exclusions": {u"alarmName": u"test.alarmName"},
            u"group_wait": u"2m",
            u"repeat_interval": "60s",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'alarm_actions': [],
            u'ok_actions': [],
            u'undetermined_actions': []
        }

        response = self.simulate_request("/v2.0/alarm-group-definitions/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(group_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_group_rule_defintion_create_with_unique_actions(self):
        return_value = self.group_def_repo_mock.return_value
        return_value.get_alarm_group_definitions.return_value = []
        return_value.create_alarm_group_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        group_def = {
            "name": "Test Definition",
            "matchers": ["alarmName", "metricName"],
            "alarm_actions": ["abc123"],
            "ok_actions": ["bcd234"],
            "undetermined_actions": ["cde345"]
        }

        expected_data = {
            u"name": u"Test Definition",
            u"matchers": [u"alarmName", u"metricName"],
            u"exclusions": [],
            u"group_wait": u"30s",
            u"repeat_interval": "2h",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'alarm_actions': ["abc123"],
            u'ok_actions': ["bcd234"],
            u'undetermined_actions': ["cde345"]
        }

        response = self.simulate_request("/v2.0/alarm-group-definitions/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(group_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_group_rule_definition_create_with_similar_actions(self):
        return_value = self.group_def_repo_mock.return_value
        return_value.get_alarm_group_definitions.return_value = []
        return_value.create_alarm_group_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        group_def = {
            "name": "Test Definition",
            "matchers": ["alarmName", "metricName"],
            "alarm_actions": ["abc123"],
            "ok_actions": ["abc123"],
            "undetermined_actions": ["abc123"]
        }

        expected_data = {
            u"name": u"Test Definition",
            u"matchers": [u"alarmName", u"metricName"],
            u"exclusions": [],
            u"group_wait": u"30s",
            u"repeat_interval": "2h",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'alarm_actions': ["abc123"],
            u'ok_actions': ["abc123"],
            u'undetermined_actions': ["abc123"]
        }

        response = self.simulate_request("/v2.0/alarm-group-definitions/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(group_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_group_rule_definition_create_with_similar_name(self):
        return_value = self.group_def_repo_mock.return_value
        return_value.get_alarm_group_definitions.return_value = [u"abc123"]
        return_value.create_alarm_group_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        group_def = {
            "name": "Test Definition",
            "matchers": ["alarmName", "metricName"]
        }

        response = self.simulate_request("/v2.0/alarm-group-definitions/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(group_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_409,
                         u"should have failed due to existing similar name")

    def test_group_rule_definition_create_without_required_fields(self):
        return_value = self.group_def_repo_mock.return_value
        return_value.get_alarm_group_definitions.return_value = [u"abc123"]
        return_value.create_alarm_group_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        group_def = {
            "name": "Test Definition",
            "matchers": ["alarmName", "metricName"]
        }

        for key, value in group_def.items():
            response = self.simulate_request("/v2.0/alarm-group-definitions/",
                                             headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                             method="POST",
                                             body=json.dumps({key: value}))

            self.assertEqual(self.srmock.status, falcon.HTTP_422,
                             u"should have failed because required field {} was missing".format(value))

    def test_group_rule_definition_update(self):
        self.group_def_repo_mock.return_value.get_alarm_group_definitions.return_value = []
        self.group_def_repo_mock.return_value.update_or_patch_alarm_group_definition.return_value = (
            {u'alarm_actions': [],
             u'ok_actions': [],
             u'id': u'00000001-0001-0001-0001-000000000001',
             u'name': u'Test Alarm',
             u'undetermined_actions': [],
             u'matchers': u'alarmName,metricName',
             u'exclusions': [],
             u'group_wait': u'30s',
             u'repeat_interval': u'2h'
             }
        )

        expected_def = {
            u'id': u'00000001-0001-0001-0001-000000000001',
            u'alarm_actions': [],
            u'ok_actions': [],
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-group-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': u'Test Alarm',
            u'undetermined_actions': [],
            u'matchers': [u'alarmName', u'metricName'],
            u'exclusions': [],
            u'group_wait': u'30s',
            u'repeat_interval': '2h'
        }

        group_def = {
            "name": "Test Definition",
            "matchers": ["alarmName", "metricName"],
            "exclusions": {},
            "group_wait": "30s",
            "repeat_interval": "2h",
            'alarm_actions': [],
            'ok_actions': [],
            'undetermined_actions': []
        }

        result = self.simulate_request("/v2.0/alarm-group-definitions/%s" % expected_def[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                       method="PUT",
                                       body=json.dumps(group_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(result[0])
        self.assertEqual(result_def, expected_def)

    def test_group_rule_definition_update_missing_fields(self):
        self.group_def_repo_mock.return_value.get_alarm_group_definitions.return_value = []
        self.group_def_repo_mock.return_value.update_or_patch_alarm_group_definition.return_value = (
            {u'alarm_actions': [],
             u'ok_actions': [],
             u'id': u'00000001-0001-0001-0001-000000000001',
             u'name': u'Test Alarm',
             u'undetermined_actions': [],
             u'matchers': u'alarmName,metricName',
             u'exclusions': [],
             u'group_wait': u'30s',
             u'repeat_interval': u'2h'
             }
        )

        expected_def = {
            u'id': u'00000001-0001-0001-0001-000000000001',
            u'alarm_actions': [],
            u'ok_actions': [],
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-group-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': u'Test Alarm',
            u'undetermined_actions': [],
            u'matchers': [u'alarmName', u'metricName'],
            u'exclusions': [],
            u'group_wait': u'30s',
            u'repeat_interval': '2h'
        }

        group_def = {
            "name": "Test Definition",
            "matchers": ["alarmName", "metricName"],
            "exclusions": {},
            "group_wait": "30s",
            "repeat_interval": "2h",
            'alarm_actions': [],
            'ok_actions': [],
            'undetermined_actions': []
        }

        result = self.simulate_request("/v2.0/alarm-group-definitions/%s" % expected_def[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                       method="PUT",
                                       body=json.dumps(group_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(result[0])
        self.assertEqual(result_def, expected_def)

        for key, value in group_def.iteritems():
            del group_def[key]
            self.simulate_request("/v2.0/alarm-group-definitions/%s" % expected_def[u'id'],
                                  headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                  method="PUT",
                                  body=json.dumps(group_def))
            self.assertEqual(self.srmock.status, "422 Unprocessable Entity",
                             u"should have failed without key {}".format(key))
            group_def[key] = value


    def test_group_rule_definition_patch(self):
        self.group_def_repo_mock.return_value.get_alarm_group_definitions.return_value = []
        new_name = u'Test Definition Updated'
        group_rule_def_id = u'00000001-0001-0001-0001-000000000001'
        matchers = ["alarmName", "metricName"]
        exclusions = {"alarmName": "test.alarmName"}
        group_wait = "1m"
        repeat_interval = "30s"
        self.group_def_repo_mock.return_value.update_or_patch_alarm_group_definition.return_value = (
            {u'alarm_actions': [],
             u'ok_actions': [],
             u'id': group_rule_def_id,
             u'name': new_name,
             u'undetermined_actions': [],
             u'matchers': u'alarmName,metricName',
             u'exclusions': exclusions,
             u'group_wait': group_wait,
             u'repeat_interval': repeat_interval
             }
        )

        expected_def = {
            u'id': group_rule_def_id,
            u'alarm_actions': [],
            u'ok_actions': [],
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-group-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': new_name,
            u'undetermined_actions': [],
            u'matchers': matchers,
            u'exclusions': exclusions,
            u'group_wait': group_wait,
            u'repeat_interval': repeat_interval
        }

        group_rule_def = {
            u'name': u'Test Definition Updated',
        }

        result = self.simulate_request("/v2.0/alarm-group-definitions/%s" % expected_def[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                       method="PATCH",
                                       body=json.dumps(group_rule_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(result[0])
        self.assertEqual(result_def, expected_def)

        ((_, event), _) = self._send_event.call_args
        fields = {u'alarm_actions': None,
                  u'ok_actions': None,
                  u'id': group_rule_def_id,
                  u'name': new_name,
                  u'undetermined_actions': None,
                  u'matchers': matchers,
                  u'exclusions': None,  # NOTE: IS THIS RIGHT???
                  u'group_wait': group_wait,
                  u'tenantId': u'ecacba9876543210fedcba9876543210',
                  u'repeat_interval': repeat_interval
                  } 
        reference = {u'alarm-group-definition-updated': fields}
        self.assertEqual(reference, event)

    def test_group_rule_definition_get_specific_rule(self):
        self.group_def_repo_mock.return_value.get_alarm_group_definition.return_value = { 
            u'alarm_actions': None,
            u'ok_actions': None,
            u'id': u'00000001-0001-0001-0001-000000000001',
            u'name': u'Test Alarm',
            u'undetermined_actions': None,
            u'matchers': u'alarmName,metricName',
            u'exclusions': {},
            u'group_wait': u'30s',
            u'repeat_interval': u'2h'
        }

        expected_data = {
            u'alarm_actions': [],
            u'ok_actions': [],
            u'id': u'00000001-0001-0001-0001-000000000001',
            u'name': u'Test Alarm',
            u'undetermined_actions': [],
            u'matchers': [u'alarmName', u'metricName'],
            u'exclusions': {},
            u'group_wait': u'30s',
            u'repeat_interval': u'2h'
        }

        response = self.simulate_request(
            '/v2.0/alarm-group-definitions/%s' % (expected_data[u'id']),
            headers={
                'X-Roles': 'admin',
                'X-Tenant-Id': TENANT_ID,
            })

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_get_alarm_definitions_with_multibyte_character(self):
        def_name = 'ａｌａｒｍ＿ｄｅｆｉｎｉｔｉｏｎ'
        if six.PY2:
            def_name = def_name.decode('utf8')
        self.group_def_repo_mock.return_value.get_alarm_group_definition.return_value = { 
            u'alarm_actions': None,
            u'ok_actions': None,
            u'id': u'00000001-0001-0001-0001-000000000001',
            u'name': def_name,
            u'undetermined_actions': None,
            u'matchers': u'alarmName,metricName',
            u'exclusions': {},
            u'group_wait': u'30s',
            u'repeat_interval': u'2h'
        }

        expected_data = {
            u'alarm_actions': [],
            u'ok_actions': [],
            u'id': u'00000001-0001-0001-0001-000000000001',
            u'name': def_name,
            u'undetermined_actions': [],
            u'matchers': [u'alarmName', u'metricName'],
            u'exclusions': {},
            u'group_wait': u'30s',
            u'repeat_interval': u'2h'
        }

        response = self.simulate_request(
            '/v2.0/alarm-group-definitions/%s' % (expected_data[u'id']),
            headers={
                'X-Roles': 'admin',
                'X-Tenant-Id': TENANT_ID,
            })

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, RESTResponseEquals(expected_data))
