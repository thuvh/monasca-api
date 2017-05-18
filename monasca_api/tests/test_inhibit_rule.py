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
from monasca_api.v2.reference import inhibit_rules

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
            'inhibit_rules_driver',
            'monasca_api.common.repositories.inhibit_rules_repository:'
            'InhibitRulesRepository',
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


class InhibitRuleTestBase(TestBase):

    def setUp(self):
        super(InhibitRuleTestBase, self).setUp()

        self.inhibit_rule_repo_mock = self.useFixture(fixtures.MockPatch(
            'monasca_api.common.repositories.inhibit_rules_repository.'
            'InhibitRulesRepository')).mock

        self.inhibit_rule_resource = inhibit_rules.InhibitRules()
        self.inhibit_rule_resource.send_event = Mock()
        self._send_event = self.inhibit_rule_resource.send_event

        self.api.add_route("/v2.0/inhibit-rules/",
                           self.inhibit_rule_resource)
        self.api.add_route("/v2.0/inhibit-rules/{inhibit_rule_id}",
                           self.inhibit_rule_resource)

    def test_inhibit_rule_create(self):
        group_rule_id = u"00000001-0001-0001-0001-000000000001"
        return_value = self.inhibit_rule_repo_mock.return_value
        return_value.get_inhibit_rules.return_value = []
        return_value.create_inhibit_rule.return_value = group_rule_id

        inhibit_rule = {
            "name": "test_inhibit_rule",
            "expression": "source metric_1 targets metric_2 excluding metric_3"
        }

        expected_data = {
            u"name": u"test_inhibit_rule",
            u"description": u"",
            u"id": group_rule_id,
            u"expression": u"source metric_1 targets metric_2 excluding metric_3"
        }

        response = self.simulate_request("/v2.0/inhibit-rules/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(inhibit_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

        ((_, event), _) = self._send_event.call_args
        fields = {u'tenantId': TENANT_ID,
                  u'id': group_rule_id,
                  u'name': "test_inhibit_rule",
                  u'source_match': {'__metricName__': 'metric_1'},
                  u'target_match': {'__metricName__': 'metric_2'},
                  u'equal': [],
                  u'exclusions': {'__metricName__': 'metric_3'}
                  }
        reference = {u'inhibit-rule-created': fields}
        self.assertEqual(reference, event)

    def test_inhibit_rule_create_with_optional_params(self):
        return_value = self.inhibit_rule_repo_mock.return_value
        return_value.get_inhibit_rules.return_value = []
        return_value.create_inhibit_rule.return_value = u"00000001-0001-0001-0001-000000000001"

        inhibit_rule = {
            "name": "test_inhibit_rule",
            "description": "test inhibit rule",
            "expression": "source metric_1 targets metric_2 excluding metric_3"
        }

        expected_data = {
            u"name": u"test_inhibit_rule",
            u"description": u"test inhibit rule",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"expression": u"source metric_1 targets metric_2 excluding metric_3"
        }

        response = self.simulate_request("/v2.0/inhibit-rules/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(inhibit_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_data))

    def test_inhibit_rule_create_with_same_name(self):
        return_value = self.inhibit_rule_repo_mock.return_value
        return_value.get_inhibit_rules.return_value = [u"00000001-0001-0001-0001-000000000001"]
        return_value.create_inhibit_rule.return_value = u"00000001-0001-0001-0001-000000000001"

        inhibit_rule = {
            "name": "test_inhibit_rule",
            "expression": "source metric_1 targets metric_2 excluding metric_3"
        }

        self.simulate_request("/v2.0/inhibit-rules/",
                              headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                              method="POST",
                              body=json.dumps(inhibit_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_409,
                         u"should have failed due to existing same name")

    def test_inhibit_rule_create_without_required_field(self):
        return_value = self.inhibit_rule_repo_mock.return_value
        return_value.get_inhibit_rules.return_value = []
        return_value.create_inhibit_rule.return_value = u"00000001-0001-0001-0001-000000000001"

        inhibit_rule = {
            "name": "test_inhibit_rule",
            "expression": "source metric_1 targets metric_2 excluding metric_3"
        }

        expected_rule = {
            u"name": u"test_inhibit_rule",
            u"description": u"",
            u"id": u"00000001-0001-0001-0001-000000000001",
            u"expression": u"source metric_1 targets metric_2 excluding metric_3"
        }

        response = self.simulate_request("/v2.0/inhibit-rules/",
                                         headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                         method="POST",
                                         body=json.dumps(inhibit_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        self.assertThat(response, RESTResponseEquals(expected_rule))

        for key, value in inhibit_rule.iteritems():
            del inhibit_rule[key]
            self.simulate_request("/v2.0/inhibit-rules/",
                                  headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                  method="POST",
                                  body=json.dumps(inhibit_rule))
            self.assertEqual(self.srmock.status, "422 Unprocessable Entity",
                             u"should have failed without key {}".format(key))
            inhibit_rule[key] = value

    def test_inhibit_rule_update(self):
        self.inhibit_rule_repo_mock.return_value.get_inhibit_rules.return_value = []
        new_name = u'test_inhibit_rule_update'
        group_rule_def_id = u'00000001-0001-0001-0001-000000000001'
        expression = u"source metric_1 targets metric_2 excluding metric_3"
        description = u"Updated Description"
        self.inhibit_rule_repo_mock.return_value.update_or_patch_inhibit_rule.return_value = (
            {u'id': group_rule_def_id,
             u'name': new_name,
             u'description': description,
             u"expression": expression
             }
        )

        expected_rule = {
            u'id': group_rule_def_id,
            u'links': [{u'href': u'http://falconframework.org/v2.0/inhibit-rules/'
                                 u'00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': new_name,
            u'description': description,
            u"expression": expression
        }

        inhibit_rule_def = {
            'name': new_name,
            'description': description,
            'expression': expression
        }
        result = self.simulate_request("/v2.0/inhibit-rules/%s" % expected_rule[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                       method="PUT",
                                       body=json.dumps(inhibit_rule_def))
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(result[0])
        print result
        self.assertEqual(result_def, expected_rule)

    def test_inhibit_rule_definition_update_missing_fields(self):
        self.inhibit_rule_repo_mock.return_value.get_inhibit_rules.return_value = []
        new_name = u'Test Definition Updated'
        group_rule_id = '00000001-0001-0001-0001-000000000001'
        expression = u"source metric_1 targets metric_2 excluding metric_3"
        description = "Updated Description"
        self.inhibit_rule_repo_mock.return_value.update_or_patch_inhibit_rule.return_value = (
            {u'id': group_rule_id,
             u'name': new_name,
             u'description': description,
             u'expression': expression
             }
        )

        expected_rule = {
            u'id': group_rule_id,
            u'links': [{u'href': u'http://falconframework.org/v2.0/inhibit-rules/'
                                 u'00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': new_name,
            u'description': description,
            u'expression': expression
        }

        inhibit_rule = {
            'name': new_name,
            'description': description,
            'expression': expression
        }

        result = self.simulate_request("/v2.0/inhibit-rules/%s" % expected_rule[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                       method="PUT",
                                       body=json.dumps(inhibit_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(result[0])
        self.assertEqual(result_def, expected_rule)

        for key, value in inhibit_rule.iteritems():
            del inhibit_rule[key]
            self.simulate_request("/v2.0/inhibit-rules/%s" % expected_rule[u'id'],
                                  headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                  method="PUT",
                                  body=json.dumps(inhibit_rule))
            self.assertEqual(self.srmock.status, falcon.HTTP_422,
                             u"Should have failed without key {}".format(key))
            inhibit_rule[key] = value

    def test_inhibit_rule_patch(self):
        self.inhibit_rule_repo_mock.return_value.get_inhibit_rules.return_value = []
        new_name = u'new_test_inhibit_rule_patch'
        group_rule_id = '00000001-0001-0001-0001-000000000001'
        expression = u"source metric_1 targets metric_2 excluding metric_3"
        self.inhibit_rule_repo_mock.return_value.update_or_patch_inhibit_rule.return_value = (
            {u'id': group_rule_id,
             u'name': new_name,
             u'description': u'',
             u'expression': expression
             }
        )

        expected_rule = {
            u'id': group_rule_id,
            u'links': [{u'href': u'http://falconframework.org/v2.0/inhibit-rules/'
                                 u'00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': new_name,
            u'description': u'',
            u'expression': expression
        }

        inhibit_rule = {
            'name': new_name
        }

        result = self.simulate_request("/v2.0/inhibit-rules/%s" % expected_rule[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID},
                                       method="PATCH",
                                       body=json.dumps(inhibit_rule))

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_def = json.loads(result[0])
        self.assertEqual(result_def, expected_rule)

        ((_, event), _) = self._send_event.call_args
        fields = {u'tenantId': TENANT_ID,
                  u'id': group_rule_id,
                  u'name': new_name,
                  u'description': '',
                  u'source_match': {'__metricName__': 'metric_1'},
                  u'target_match': {'__metricName__': 'metric_2'},
                  u'equal': [],
                  u'exclusions': {'__metricName__': 'metric_3'}
                  }
        reference = {u'inhibit-rule-updated': fields}
        self.assertEqual(reference, event)

    def test_inhibit_rule_get_specific_rule(self):
        new_name = u'test_get_inhibit_rule'
        group_rule_id = '00000001-0001-0001-0001-000000000001'
        self.inhibit_rule_repo_mock.return_value.get_inhibit_rule.return_value = (
            {u'id': group_rule_id,
             u'name': new_name,
             u'description': u'',
             u'expression': u"source metric_1 targets metric_2 excluding metric_3"
             }
        )

        expected_def = {
            u'id': group_rule_id,
            u'links': [{u'href': u'http://falconframework.org/v2.0/inhibit-rules/'
                                 u'00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': new_name,
            u'description': u'',
            u'expression': u"source metric_1 targets metric_2 excluding metric_3"
        }

        result = self.simulate_request("/v2.0/inhibit-rules/%s" % expected_def[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID})

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(result, RESTResponseEquals(expected_def))

    def test_get_inhibit_rule_with_multibyte_character(self):
        def_name = 'ａｌａｒｍ＿ｄｅｆｉｎｉｔｉｏｎ'
        if six.PY2:
            def_name = def_name.decode('utf8')
        group_rule_def_id = '00000001-0001-0001-0001-000000000001'
        self.inhibit_rule_repo_mock.return_value.get_inhibit_rule.return_value = (
            {u'id': group_rule_def_id,
             u'name': def_name,
             u'description': u'',
             u'expression': u"source metric_1 targets metric_2 excluding metric_3"
             }
        )

        expected_def = {
            u'id': group_rule_def_id,
            u'links': [{u'href': u'http://falconframework.org/v2.0/inhibit-rules/'
                                 u'00000001-0001-0001-0001-000000000001',
                        u'rel': u'self'}],
            u'name': def_name,
            u'description': u'',
            u'expression': u"source metric_1 targets metric_2 excluding metric_3"
        }

        result = self.simulate_request("/v2.0/inhibit-rules/%s" % expected_def[u'id'],
                                       headers={'X-Roles': 'admin', 'X-Tenant-Id': TENANT_ID})

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(result, RESTResponseEquals(expected_def))
