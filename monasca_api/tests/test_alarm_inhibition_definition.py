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
from monasca_api.v2.reference import alarm_inhibition_definitions

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
            'alarm_inhibition_definitions_driver',
            'monasca_api.common.repositories.alarm_inhibition_definitions_repository:'
            'AlarmInhibitionDefinitionsRepository',
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


class InhibitionRuleDefinitionTestBase(AlarmTestBase):

    def setUp(self):
        super(InhibitionRuleDefinitionTestBase, self).setUp()

        self.inhibition_def_repo_mock = self.useFixture(fixtures.MockPatch(
            'monasca_api.common.repositories.alarm_inhibition_definitions_repository.'
            'AlarmInhibitionDefinitionsRepository'
        )).mock

        self.inhibition_definition_resource = alarm_inhibition_definitions.AlarmInhibitionDefinitions()
        self.inhibition_definition_resource.send_event = Mock()
        self._send_event = self.inhibition_definition_resource.send_event

        self.api.add_route("/v2.0/alarm-inhibition-definitions/",
                           self.inhibition_definition_resource)
        self.api.add_route("/v2.0/alarm-inhibition-definitions/{alarm_inhibition_definition_id}",
                           self.inhibition_definition_resource)

    def test_inhibition_rule_definition_create(self):
        return_value = self.inhibition_def_repo_mock.return_value
        return_value.get_alarm_inhibition_definitions.return_value = []
        return_value.create_alarm_inhibition_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        inhibition_def = {
            "name": "Test Definition",
            "equal": ["alarmName", "metricName"],
            "source_match": {"severity": "CRITICAL"},
            "target_match": {"severity": "LOW"}
        }

        expected_data = {
            u"name": u"Test Definition",
            u"description": u"",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"equal": ["alarmName", "metricName"],
            u"source_match": {"severity": "CRITICAL"},
            u"target_match": {"severity": "LOW"},
            u"exclusions": {}
        }

        response = self.simulate_request("/v2.0/alarm-inhibition-definitions/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(inhibition_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_inhibition_rule_definition_create_with_optional_params(self):
        return_value = self.inhibition_def_repo_mock.return_value
        return_value.get_alarm_inhibition_definitions.return_value = []
        return_value.create_alarm_inhibition_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        inhibition_def = {
            "name": "Test Definition",
            "description": "Test Description",
            "equal": ["alarmName", "metricName"],
            "source_match": {"severity": "CRITICAL"},
            "target_match": {"severity": "LOW"},
            "exclusions": {"alarmName": "test.alarmName"}
        }

        expected_data = {
            u"name": u"Test Definition",
            u"description": u"Test Description",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"equal": ["alarmName", "metricName"],
            u"source_match": {"severity": "CRITICAL"},
            u"target_match": {"severity": "LOW"},
            u"exclusions": {"alarmName": "test.alarmName"}
        }

        response = self.simulate_request("/v2.0/alarm-inhibition-definitions/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(inhibition_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_inhibition_rule_definition_create_with_similar_name(self):
        return_value = self.inhibition_def_repo_mock.return_value
        return_value.get_alarm_inhibition_definitions.return_value = [u"00000001-0001-0001-0001-000000000001"]
        return_value.create_alarm_inhibition_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        inhibition_def = {
            "name": "Test Definition",
            "equal": ["alarmName", "metricName"],
            "source_match": {"severity": "CRITICAL"},
            "target_match": {"severity": "LOW"},
            "exclusions": {"alarmName": "test.alarmName"}
        }

        self.simulate_request("/v2.0/alarm-inhibition-definitions/",
                              headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                              method="POST",
                              body=json.dumps(inhibition_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_409,
                         u"should have failed due to existing similar name")

    def test_inhibition_rule_definition_create_without_required_field(self):
        return_value = self.inhibition_def_repo_mock.return_value
        return_value.get_alarm_inhibition_definitions.return_value = []
        return_value.create_alarm_inhibition_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        inhibition_def = {
            "name": "Test Definition",
            "equal": ["alarmName", "metricName"],
            "source_match": {"severity": "CRITICAL"},
            "target_match": {"severity": "LOW"}
        }

        expected_def = {
            u"name": u"Test Definition",
            u"description": u"",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"equal": ["alarmName", "metricName"],
            u"source_match": {"severity": "CRITICAL"},
            u"target_match": {"severity": "LOW"},
            u"exclusions": {}
        }

        response = self.simulate_request("/v2.0/alarm-inhibition-definitions/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(inhibition_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_def))

        for key, value in inhibition_def.iteritems():
            del inhibition_def[key]
            self.simulate_request("/v2.0/alarm-inhibition-definitions/",
                                  headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                  method="POST",
                                  body=json.dumps(inhibition_def))
            self.assertEqual(self.srmock.status, "422 Unprocessable Entity",
                             u"should have failed without key {}".format(key))
            inhibition_def[key] = value

    def test_inhibition_rule_definition_update(self):
        self.inhibition_def_repo_mock.return_value.get_alarm_inhibition_definitions.return_value = []
        new_name = u'Test Definition Updated'
        group_rule_def_id = '00000001-0001-0001-0001-000000000001'
        equal = ["alarmName", "metricName"]
        source_match = {"severity": "CRITICAL"}
        target_match = {"severity": "LOW"}
        exclusions = {"alarmName": "test.alarmName"}
        description = "Updated Description"
        self.inhibition_def_repo_mock.return_value.update_or_patch_alarm_inhibition_definition.return_value = (
            {u'id': group_rule_def_id,
             u'name': new_name,
             u'description': description,
             u'exclusion': "alarmName=test.alarmName",
             u'equal': "alarmName,metricName",
             u'source_match': "severity=CRITICAL",
             u'target_match': "severity=LOW"
             }
        )

        expected_def = {
            u'id': group_rule_def_id,
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-inhibition-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': new_name,
            u'description': description,
            u'exclusions': exclusions,
            u'equal': equal,
            u'source_match': source_match,
            u'target_match': target_match
        }

        inhibition_rule_def = {
            'name': new_name,
            'description': description,
            'exclusions': exclusions,
            'equal': equal,
            'source_match': source_match,
            'target_match': target_match
        }
        result = self.simulate_request("/v2.0/alarm-inhibition-definitions/%s" % expected_def[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                       method="PUT",
                                       body=json.dumps(inhibition_rule_def))
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(result[0])
        self.assertEqual(result_def, expected_def)

    def test_inhibition_rule_definition_update_missing_fields(self):
        self.inhibition_def_repo_mock.return_value.get_alarm_inhibition_definitions.return_value = []
        new_name = u'Test Definition Updated'
        group_rule_def_id = '00000001-0001-0001-0001-000000000001'
        equal = ["alarmName", "metricName"]
        source_match = {"severity": "CRITICAL"}
        target_match = {"severity": "LOW"}
        exclusions = {"alarmName": "test.alarmName"}
        description = "Updated Description"
        self.inhibition_def_repo_mock.return_value.update_or_patch_alarm_inhibition_definition.return_value = (
            {u'id': group_rule_def_id,
             u'name': new_name,
             u'description': description,
             u'exclusion': "alarmName=test.alarmName",
             u'equal': "alarmName,metricName",
             u'source_match': "severity=CRITICAL",
             u'target_match': "severity=LOW"
             }
        )

        expected_def = {
            u'id': group_rule_def_id,
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-inhibition-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': new_name,
            u'description': description,
            u'exclusions': exclusions,
            u'equal': equal,
            u'source_match': source_match,
            u'target_match': target_match
        }

        inhibition_rule_def = {
            'name': new_name,
            'description': description,
            'exclusions': exclusions,
            'equal': equal,
            'source_match': source_match,
            'target_match': target_match
        }

        result = self.simulate_request("/v2.0/alarm-inhibition-definitions/%s" % expected_def[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                       method="PUT",
                                       body=json.dumps(inhibition_rule_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(result[0])
        self.assertEqual(result_def, expected_def)

        for key, value in inhibition_rule_def.iteritems():
            del inhibition_rule_def[key]
            self.simulate_request("/v2.0/alarm-inhibition-definitions/%s" % expected_def[u'id'],
                                  headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                  method="PUT",
                                  body=json.dumps(inhibition_rule_def))
            self.assertEqual(self.srmock.status, falcon.HTTP_422,
                             u"Should have failed without key {}".format(key))
            inhibition_rule_def[key] = value

    def test_inhibition_rule_defintion_patch(self):
        self.inhibition_def_repo_mock.return_value.get_alarm_inhibition_definitions.return_value = []
        new_name = u'Test Definition Updated'
        group_rule_def_id = '00000001-0001-0001-0001-000000000001'
        equal = [u"alarmName", u"metricName"]
        source_match = {u"severity": u"CRITICAL"}
        target_match = {u"severity": u"LOW"}
        exclusions = {u"alarmName": u"test.alarmName"}
        self.inhibition_def_repo_mock.return_value.update_or_patch_alarm_inhibition_definition.return_value = (
            {u'id': group_rule_def_id,
             u'name': new_name,
             u'description': u'',
             u'exclusion': "alarmName=test.alarmName",
             u'equal': "alarmName,metricName",
             u'source_match': "severity=CRITICAL",
             u'target_match': "severity=LOW"
             }
        )

        expected_def = {
            u'id': group_rule_def_id,
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-inhibition-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': new_name,
            u'description': u'',
            u'exclusions': exclusions,
            u'equal': equal,
            u'source_match': source_match,
            u'target_match': target_match
        }

        inhibition_rule_def = {
            'name': new_name
        }

        result = self.simulate_request("/v2.0/alarm-inhibition-definitions/%s" % expected_def[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                       method="PATCH",
                                       body=json.dumps(inhibition_rule_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(result[0])
        self.assertEqual(result_def, expected_def)

        ((_, event), _) = self._send_event.call_args
        fields = {u'id': group_rule_def_id,
                  u'name': new_name,
                  u'description': '',
                  u'exclusions': exclusions,
                  u'equal': equal,
                  u'source_match': source_match,
                  u'target_match': target_match,
                  u'tenantId': TENANT_ID
                  }
        reference = {u'alarm-inhibition-definition-updated': fields}
        self.assertEqual(reference, event)

    def test_inhibition_rule_definition_get_specific_rule(self):
        new_name = u'Test Definition Updated'
        group_rule_def_id = '00000001-0001-0001-0001-000000000001'
        self.inhibition_def_repo_mock.return_value.get_alarm_inhibition_definition.return_value = (
            {u'id': group_rule_def_id,
             u'name': new_name,
             u'description': u'',
             u'exclusion': "alarmName=test.alarmName",
             u'equal': "alarmName,metricName",
             u'source_match': "severity=CRITICAL",
             u'target_match': "severity=LOW"
             }
        )

        expected_def = {
            u'id': group_rule_def_id,
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-inhibition-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': new_name,
            u'description': u'',
            u'exclusions': {'alarmName': 'test.alarmName'},
            u'equal': ['alarmName', 'metricName'],
            u'source_match': {'severity': 'CRITICAL'},
            u'target_match': {'severity': 'LOW'}
        }

        result = self.simulate_request("/v2.0/alarm-inhibition-definitions/%s" % expected_def[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID})

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(result, RESTResponseEquals(expected_def))

    def test_get_alarm_inhibition_definition_with_multibyte_character(self):
        def_name = 'ａｌａｒｍ＿ｄｅｆｉｎｉｔｉｏｎ'
        if six.PY2:
            def_name = def_name.decode('utf8')
        group_rule_def_id = '00000001-0001-0001-0001-000000000001'
        self.inhibition_def_repo_mock.return_value.get_alarm_inhibition_definition.return_value = (
            {u'id': group_rule_def_id,
             u'name': def_name,
             u'description': u'',
             u'exclusion': "alarmName=test.alarmName",
             u'equal': "alarmName,metricName",
             u'source_match': "severity=CRITICAL",
             u'target_match': "severity=LOW"
             }
        )

        expected_def = {
            u'id': group_rule_def_id,
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-inhibition-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': def_name,
            u'description': u'',
            u'exclusions': {u'alarmName': u'test.alarmName'},
            u'equal': [u'alarmName', u'metricName'],
            u'source_match': {u'severity': u'CRITICAL'},
            u'target_match': {u'severity': u'LOW'}
        }

        result = self.simulate_request("/v2.0/alarm-inhibition-definitions/%s" % expected_def[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID})

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(result, RESTResponseEquals(expected_def))
