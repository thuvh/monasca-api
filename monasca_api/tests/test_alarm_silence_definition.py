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
from monasca_api.v2.reference import alarm_silence_definitions

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
            'alarm_silence_definitions_driver',
            'monasca_api.common.repositories.alarm_silence_definitions_repository:AlarmSilenceDefinitionsRepository',
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


class SilenceRuleDefinitionTestBase(AlarmTestBase):

    def setUp(self):
        super(SilenceRuleDefinitionTestBase, self).setUp()

        self.silence_def_repo_mock = self.useFixture(fixtures.MockPatch(
            'monasca_api.common.repositories.alarm_silence_definitions_repository.AlarmSilenceDefinitionsRepository'
        )).mock

        self.silence_definition_resource = alarm_silence_definitions.AlarmSilenceDefinitions()
        self.silence_definition_resource.send_event = Mock()
        self._send_event = self.silence_definition_resource.send_event

        self.api.add_route("/v2.0/alarm-silence-definitions/",
                           self.silence_definition_resource)
        self.api.add_route("/v2.0/alarm-silence-definitions/{alarm_silence_definition_id}",
                           self.silence_definition_resource)

        self.trap = []

    def test_silence_rule_definition_create(self):
        return_value = self.silence_def_repo_mock.return_value
        return_value.get_alarm_silence_definitions.return_value = []
        return_value.create_alarm_silence_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        silence_def = {
            "name": "Test Definition",
            "matchers": {"alarmName": "test.AlarmName"},
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        expected_data = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"matchers": {u"alarmName": u"test.AlarmName"},
            u"name": u"Test Definition",
            u"description": u"",
            u"silence_duration": "10m",
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/alarm-silence-definitions/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(silence_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_silence_rule_definition_create_with_optional_params(self):
        return_value = self.silence_def_repo_mock.return_value
        return_value.get_alarm_silence_definitions.return_value = []
        return_value.create_alarm_silence_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        silence_def = {
            "name": "Test Definition",
            "description": "Test Description",
            "matchers": {"alarmName": "test.AlarmName"},
            "silence_duration": "1d2h",
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        expected_data = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"matchers": {u"alarmName": u"test.AlarmName"},
            u"name": u"Test Definition",
            u"description": u"Test Description",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/alarm-silence-definitions/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(silence_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_silence_rule_definition_create_with_similar_name(self):
        return_value = self.silence_def_repo_mock.return_value
        return_value.get_alarm_silence_definitions.return_value = ["123abc"]
        return_value.create_alarm_silence_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        silence_def = {
            "name": "Test Definition",
            "matchers": {"alarmName": "test.AlarmName"},
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        self.simulate_request("/v2.0/alarm-silence-definitions/",
                              headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                              method="POST",
                              body=json.dumps(silence_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_409,
                         u"Should have failed due to existing similar name")

    def test_silence_rule_definition_create_without_required_fields(self):
        return_value = self.silence_def_repo_mock.return_value
        return_value.get_alarm_silence_definitions.return_value = []
        return_value.create_alarm_silence_definition.return_value = u"00000001-0001-0001-0001-000000000001"

        silence_def = {
            "matchers": {"alarmName": "test.AlarmName"},
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        self.simulate_request("/v2.0/alarm-silence-definitions/",
                              headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                              method="POST",
                              body=json.dumps(silence_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_422,
                         "should have failed becasue required field name was missing")

        silence_def = {
            "name": "Test Definition",
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        self.simulate_request("/v2.0/alarm-silence-definitions/",
                              headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                              method="POST",
                              body=json.dumps(silence_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_422,
                         "should have failed becasue required field matchers was missing")

    def test_silence_rule_definition_update(self):
        self.silence_def_repo_mock.return_value.get_alarm_silence_definitions.return_value = []
        self.silence_def_repo_mock.return_value.update_or_patch_alarm_silence_definition.return_value = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"name": u"Test Definition",
            u"matchers": "alarmName=test.AlarmName",
            u"description": u"Updated Test Description",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        silence_def = {
            "name": "Test Definition",
            "matchers": {"alarmName": "test.AlarmName"},
            "description": "Updated Test Description",
            "silence_duration": "1d2h",
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        expected_def = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-silence-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u"matchers": {u"alarmName": "test.AlarmName"},
            u"name": u"Test Definition",
            u"description": u"Updated Test Description",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/alarm-silence-definitions/%s" % expected_def[u'id'],
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="PUT",
                                         body=json.dumps(silence_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(response[0])
        self.assertEqual(result_def, expected_def)

    def test_silence_rule_definition_update_missing_fileds(self):
        self.silence_def_repo_mock.return_value.get_alarm_silence_definitions.return_value = []
        self.silence_def_repo_mock.return_value.update_or_patch_alarm_silence_definition.return_value = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"matchers": "alarmName=test.AlarmName",
            u"name": u"Test Definition",
            u"description": u"Updated Test Description",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        silence_def = {
            "name": "Test Definition",
            "matchers": {"alarmName": "test.AlarmName"},
            "description": "Updated Test Description",
            "silence_duration": "1d2h",
            "start_time": "2017-04-10T10:42:10.685Z"
        }

        expected_def = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-silence-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u"matchers": {u"alarmName": "test.AlarmName"},
            u"name": u"Test Definition",
            u"description": u"Updated Test Description",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/alarm-silence-definitions/%s" % expected_def[u'id'],
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="PUT",
                                         body=json.dumps(silence_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(response[0])
        self.assertEqual(result_def, expected_def)

        for key, value in silence_def.iteritems():
            del silence_def[key]
            self.simulate_request("/v2.0/alarm-silence-definitions/%s" % expected_def[u'id'],
                                  headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                  method="PUT",
                                  body=json.dumps(silence_def))
            self.assertEqual(self.srmock.status, "422 Unprocessable Entity",
                             u"should have failed without key {}".format(key))
            silence_def[key] = value

    def test_silence_rule_definition_patch(self):
        self.silence_def_repo_mock.return_value.get_alarm_silence_definitions.return_value = []
        self.silence_def_repo_mock.return_value.update_or_patch_alarm_silence_definition.return_value = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"matchers": "alarmName=test.AlarmName",
            u"name": u"Test Definition",
            u"description": u"Updated Test Description",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        silence_def = {
            "name": "Test Definition",
        }

        expected_def = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-silence-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u"matchers": {u"alarmName": "test.AlarmName"},
            u"name": u"Test Definition",
            u"description": u"Updated Test Description",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/alarm-silence-definitions/%s" % expected_def[u'id'],
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="PATCH",
                                         body=json.dumps(silence_def))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(response[0])
        self.assertEqual(result_def, expected_def)

        ((_, event), _) = self._send_event.call_args
        fields = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"matchers": {"alarmName": "test.AlarmName"},
            u"name": u"Test Definition",
            u"description": u"Updated Test Description",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z",
            u'tenantId': TENANT_ID
        }
        reference = {u'alarm-silence-definition-updated': fields}
        self.assertEqual(reference, event)

    def test_silence_rule_definition_get_specific_rule(self):
        self.silence_def_repo_mock.return_value.get_alarm_silence_definition.return_value = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"matchers": "alarmName=test.AlarmName",
            u"name": u"Test Definition",
            u"description": u"Updated Test Description",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        expected_def = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-silence-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u"matchers": {u"alarmName": "test.AlarmName"},
            u"name": u"Test Definition",
            u"description": u"Updated Test Description",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/alarm-silence-definitions/%s" % expected_def[u'id'],
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID})

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, RESTResponseEquals(expected_def))

    def test_silence_rule_definition_get_specific_rule_with_multibyte_character(self):
        def_name = 'ａｌａｒｍ＿ｄｅｆｉｎｉｔｉｏｎ'
        if six.PY2:
            def_name = def_name.decode('utf8')
        self.silence_def_repo_mock.return_value.get_alarm_silence_definition.return_value = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"matchers": "alarmName=test.AlarmName",
            u"name": def_name,
            u"description": u"Updated Test Description",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        expected_def = {
            u"id": u"00000001-0001-0001-0001-000000000001",
            u'links': [{u'href': u'http://falconframework.org/v2.0/alarm-silence-definitions/'
                                 u'00000001-0001-0001-0001-000000000001/00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u"matchers": {u"alarmName": u"test.AlarmName"},
            u"name": def_name,
            u"description": u"Updated Test Description",
            u"silence_duration": u"1d2h",
            u"start_time": u"2017-04-10T10:42:10.685Z"
        }

        response = self.simulate_request("/v2.0/alarm-silence-definitions/%s" % expected_def[u'id'],
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID})

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, RESTResponseEquals(expected_def))
