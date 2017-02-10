# -*- coding: utf-8 -*-
# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
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

import six.moves.urllib.parse as urlparse
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions
from tempest import test

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import constants
from monasca_tempest_tests.tests.api import helpers


NUM_GROUP_DEFINITIONS = 2


class TestAlarmGroupDefinitions(base.BaseMonascaTest):

    # Create

    @test.attr(type="gate")
    def test_create_group_rule_definition(self):
        # Create a group rule definition
        name = data_utils.rand_name('group_rule_definition')
        matchers = ['alarmName', 'metricName']
        group_rule_definition = helpers.create_group_definition(
            name=name, matchers=matchers)
        resp, response_body = self.monasca_client.create_group_definitions(
            group_rule_definition)

        self._verify_create_group_definitions(resp, response_body,
                                              group_rule_definition)

    @test.attr(type="gate")
    def test_create_group_rule_definition_with_notifications(self):
        notification_name = data_utils.rand_name('notification-')
        notification_type = 'EMAIL'
        notification_address = 'root@localhost'
        resp, response_body = self.monasca_client.create_notification_method(
            name=notification_name, type=notification_type,
            address=notification_address)
        notification_id = self._verify_create_notification_method(
            resp, response_body, notification_name, notification_type,
            notification_address)

        # Create a group rule definition
        name = data_utils.rand_name('group_rule_definition')
        matchers = ['alarmName', 'metricName']
        group_rule_definition = helpers.create_group_definition(
            name=name, matchers=matchers, alarm_actions=[notification_id],
            ok_actions=[notification_id],
            undetermined_actions=[notification_id])
        resp, response_body = self.monasca_client.create_group_definitions(
            group_rule_definition)

        self._verify_create_group_definitions(resp, response_body,
                                              group_rule_definition)
        self.assertEqual(notification_id, response_body['ok_actions'][0])
        self.assertEqual(notification_id, response_body['alarm_actions'][0])
        self.assertEqual(notification_id,
                         response_body['undetermined_actions'][0])

        self._delete_notification(notification_id)

    @test.attr(type="gate")
    def test_create_group_rule_definition_with_multiple_notifications(self):
        notification_name1 = data_utils.rand_name('notification-')
        notification_type1 = 'EMAIL'
        address1 = 'root@localhost'

        notification_name2 = data_utils.rand_name('notification-')
        notification_type2 = 'PAGERDUTY'
        address2 = 'http://localhost.com'

        resp, response_body = self.monasca_client.create_notification_method(
            notification_name1, type=notification_type1, address=address1)
        notification_id1 = self._verify_create_notification_method(
            resp, response_body, notification_name1, notification_type1,
            address1)
        resp, response_body = self.monasca_client.create_notification_method(
            notification_name2, type=notification_type2, address=address2)
        notification_id2 = self._verify_create_notification_method(
            resp, response_body, notification_name2, notification_type2,
            address2)

        # Create a group rule definition
        name = data_utils.rand_name('group_rule_definition')
        matchers = ['alarmName', 'metricName']
        group_rule_definition = helpers.create_group_definition(
            name=name, matchers=matchers,
            alarm_actions=[notification_id1, notification_id2],
            ok_actions=[notification_id1, notification_id2],
            undetermined_actions=[notification_id1, notification_id2])
        resp, response_body = self.monasca_client.create_group_definitions(
            group_rule_definition)

        self._verify_create_group_definitions(resp, response_body,
                                              group_rule_definition)

        self._delete_notification(notification_id1)
        self._delete_notification(notification_id2)

    @test.attr(type="gate")
    def test_create_group_rule_definition_with_optional_params(self):
        notification_name = data_utils.rand_name('notification-')
        notification_type = 'EMAIL'
        notification_address = 'root@localhost'
        resp, response_body = self.monasca_client.create_notification_method(
            name=notification_name, type=notification_type,
            address=notification_address)
        notification_id = self._verify_create_notification_method(
            resp, response_body, notification_name, notification_type,
            notification_address)

        # Create a group rule definition
        name = data_utils.rand_name('group_rule_definition')
        matchers = ['alarmName', 'metricName']
        group_wait = '1d2h5m30s'
        repeat_interval = '2d3h10m45s'
        exclusions = {'alarmName': 'alarm1', 'metricName': 'metric1'}
        description = "Test Description"
        group_rule_definition = helpers.create_group_definition(
            name=name, matchers=matchers, alarm_actions=[notification_id],
            ok_actions=[notification_id], repeat_interval=repeat_interval,
            undetermined_actions=[notification_id], group_wait=group_wait,
            exclusions=exclusions, description=description)
        resp, response_body = self.monasca_client.create_group_definitions(
            group_rule_definition)

        self._verify_create_group_definitions(resp, response_body,
                                              group_rule_definition)

        self._delete_notification(notification_id)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_create_group_rule_definition_with_name_exceeds_max_length(self):
        long_name = "x" * (constants.MAX_ALARM_DEFINITION_NAME_LENGTH + 1)
        matchers = ['alarmName', 'metricName']
        group_rule_definition = helpers.create_group_definition(
            name=long_name, matchers=matchers)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_group_definitions,
                          group_rule_definition)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_create_group_rule_definition_with_description_exceeds_max_length(self):
        name = data_utils.rand_name('group_rule_definition')
        long_description = "x" * (constants.
                                  MAX_ALARM_DEFINITION_DESCRIPTION_LENGTH + 1)
        matchers = ['alarmName', 'metricName']
        group_rule_definition = helpers.create_group_definition(
            name=name, description=long_description, matchers=matchers)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_group_definitions,
                          group_rule_definition)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_create_group_rule_definition_with_alarm_actions_exceeds_max_length(
            self):
        name = data_utils.rand_name('group_rule_definition')
        matchers = ['alarmName', 'metricName']
        alarm_actions = ["x" * (
            constants.MAX_ALARM_DEFINITION_ACTIONS_LENGTH + 1)]
        group_rule_definition = helpers.create_group_definition(
            name=name,
            matchers=matchers,
            alarm_actions=alarm_actions)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_group_definitions,
                          group_rule_definition)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_create_group_rule_definition_with_ok_actions_exceeds_max_length(
            self):
        name = data_utils.rand_name('group_rule_definition')
        matchers = ['alarmName', 'metricName']
        ok_actions = ["x" * (
            constants.MAX_ALARM_DEFINITION_ACTIONS_LENGTH + 1)]
        group_rule_definition = helpers.create_group_definition(
            name=name,
            matchers=matchers,
            ok_actions=ok_actions)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_group_definitions,
                          group_rule_definition)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_create_group_rule_definition_with_undeterm_actions_exceeds_max_length(
            self):
        name = data_utils.rand_name('group_rule_definition')
        matchers = ['alarmName', 'metricName']
        undetermined_actions = ["x" * (
            constants.MAX_ALARM_DEFINITION_ACTIONS_LENGTH + 1)]
        group_rule_definition = helpers.create_group_definition(
            name=name,
            matchers=matchers,
            undetermined_actions=undetermined_actions)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_group_definitions,
                          group_rule_definition)

    # List

    @test.attr(type="gate")
    def test_list_group_rule_definitions(self):
        matchers = ['alarmName', 'metricName']
        response_body_list = self._create_group_definitions(
            matchers=matchers, number_of_definitions=1)
        query_param = '?name=' + str(response_body_list[0]['name'])
        resp, response_body = self.monasca_client.list_group_definitions(
            query_param)

        # Test list alarm definition response body
        self._verify_list_group_definitions_response_body(resp, response_body)

        elements = response_body['elements']
        self._verify_group_definitions_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_group_definitions_links(links)

    @test.attr(type="gate")
    def test_list_group_rule_definitions_with_multibyte_character(self):
        name = data_utils.rand_name('ｄｅｆｉｎｉｔｉｏｎ').decode('utf8')
        description = 'ｄｅｓｃｒｉｐｔｉｏｎ'.decode('utf8')
        matchers = ['alarmName', 'metricName']
        response_body_list = self._create_group_definitions(
            name=name, matchers=matchers, description=description,
            number_of_definitions=1)
        query_param = '?name=' + urlparse.quote(name.encode('utf8'))
        resp, response_body = self.monasca_client.list_group_definitions(
            query_param)

        # Test list alarm definition response body
        self._verify_list_group_definitions_response_body(resp, response_body)

        elements = response_body['elements']
        self._verify_group_definitions_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_group_definitions_links(links)

    @test.attr(type="gate")
    def test_list_group_rule_definitions_with_name(self):
        name = data_utils.rand_name('group_rule_definition')
        matchers = ['alarmName', 'metricName']
        description = data_utils.rand_name('description')
        group_definition = helpers.create_group_definition(
            name=name,
            description=description,
            matchers=matchers)
        resp_create, response_body_create = self.monasca_client.\
            create_group_definitions(group_definition)
        self.assertEqual(201, resp_create.status)

        query_parms = "?name=" + str(name)
        resp, response_body = self.monasca_client.list_group_definitions(
            query_parms)

        # Test list alarm definition response body
        self._verify_list_group_definitions_response_body(resp, response_body)

        elements = response_body['elements']
        self._verify_group_definitions_list(elements, [response_body_create])

        links = response_body['links']
        self._verify_list_group_definitions_links(links)

    @test.attr(type="gate")
    def test_list_group_rule_definitions_with_offset_limit(self):
        helpers.delete_group_definitions(self.monasca_client)
        matchers = ['alarmName', 'metricName']
        self._create_group_definitions(
            matchers=matchers, number_of_definitions=NUM_GROUP_DEFINITIONS)
        resp, response_body = self.monasca_client.list_group_definitions()

        self._verify_list_group_definitions_response_body(resp, response_body)
        first_element = response_body['elements'][0]
        last_element = response_body['elements'][1]

        query_parms = '?limit=2'
        resp, response_body = self.monasca_client.list_group_definitions(
            query_parms)
        self.assertEqual(200, resp.status)

        elements = response_body['elements']
        self.assertEqual(2, len(elements))
        self.assertEqual(first_element, elements[0])
        self.assertEqual(last_element, elements[1])

        for offset in xrange(0, 2):
            for limit in xrange(1, 3 - offset):
                query_parms = '?offset=' + str(offset) + '&limit=' + str(limit)
                resp, response_body = self.monasca_client.list_group_definitions(query_parms)
                self.assertEqual(200, resp.status)
                new_elements = response_body['elements']
                self.assertEqual(limit, len(new_elements))
                self.assertEqual(elements[offset], new_elements[0])
                self.assertEqual(elements[offset + limit - 1],
                                 new_elements[-1])
                links = response_body['links']
                for link in links:
                    if link['rel'] == 'next':
                        next_offset = helpers.get_query_param(link['href'], 'offset')
                        next_limit = helpers.get_query_param(link['href'], 'limit')
                        self.assertEqual(str(offset + limit), next_offset)
                        self.assertEqual(str(limit), next_limit)

    # Get

    @test.attr(type="gate")
    def test_get_group_rule_definitions(self):
        response_body_list = self._create_group_definitions(
            number_of_definitions=1)
        resp, response_body = self.monasca_client.get_group_definition(
            response_body_list[0]['id'])
        self.assertEqual(200, resp.status)
        self._verify_element_set(response_body)
        self._verify_group_definitions_element(response_body,
                                               response_body_list[0])
        links = response_body['links']
        self._verify_list_group_definitions_links(links)

    @test.attr(type="gate")
    def test_get_group_rule_definitions_with_multibyte_character(self):
        name = data_utils.rand_name('ｄｅｆｉｎｉｔｉｏｎ').decode('utf8')
        description = 'ｄｅｓｃｒｉｐｔｉｏｎ'.decode('utf8')
        matchers = ['alarmName', 'metricName']
        response_body_list = self._create_group_definitions(
            name=name, matchers=matchers, description=description,
            number_of_definitions=1)
        group_definition = response_body_list[0]

        resp, response_body = self.monasca_client.get_group_definition(
            group_definition['id'])

        self.assertEqual(200, resp.status)
        self._verify_element_set(response_body)
        self._verify_group_definitions_element(response_body,
                                               group_definition)
        links = response_body['links']
        self._verify_list_group_definitions_links(links)

    @test.attr(type="gate")
    @test.attr(type="negative")
    def test_get_group_rule_definitions_with_invalid_id(self):
        def_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.get_group_definition, def_id)

    # Update

    @test.attr(type="gate")
    def test_update_group_rule_definitions(self):
        notification_name = data_utils.rand_name('notification-')
        notification_type = 'EMAIL'
        address = 'root@localhost'

        resp, response_body = self.monasca_client.create_notification_method(
            notification_name, type=notification_type, address=address)
        notification_id = self._verify_create_notification_method(
            resp, response_body, notification_name, notification_type, address)

        matchers = ['alarmName']
        exclusions = {'alarmName': 'alarm1'}

        response_body_list = self._create_group_definitions(
            number_of_definitions=1, matchers=matchers,
            exclusions=exclusions)
        # Update group definition
        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_group_wait = '1h5m'
        updated_repeat_interval = '45s'

        resp, response_body = self.monasca_client.update_group_definition(
            str(response_body_list[0]['id']), updated_name, updated_description,
            matchers, updated_group_wait, updated_repeat_interval,
            exclusions, [notification_id], [notification_id],
            [notification_id])
        self.assertEqual(200, resp.status)
        self._verify_update_patch_group_definition(response_body,
                                                   updated_name,
                                                   updated_description,
                                                   updated_group_wait,
                                                   updated_repeat_interval,
                                                   notification_id)
        # Validate fields updated
        resp, response_body = self.monasca_client.get_group_definition(
            response_body_list[0]['id'])
        self._verify_update_patch_group_definition(response_body,
                                                   updated_name,
                                                   updated_description,
                                                   updated_group_wait,
                                                   updated_repeat_interval,
                                                   notification_id)
        links = response_body['links']
        self._verify_list_group_definitions_links(links)

    @test.attr(type="gate")
    @test.attr(type="negative")
    def test_update_group_rule_definitions_with_matchers_or_exclusions(self):

        # Update group definition
        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_group_wait = '1h5m'
        updated_repeat_interval = '45s'
        matchers = ['alarmName']
        exclusions = {'alarmName': 'alarm1'}

        response_body_list = self._create_group_definitions(
            number_of_definitions=1, matchers=matchers,
            exclusions=exclusions)

        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.update_group_definition,
                          str(response_body_list[0]['id']), updated_name,
                          updated_description, ['metricName'],
                          updated_group_wait, updated_repeat_interval,
                          exclusions, [], [], [])

        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.update_group_definition,
                          str(response_body_list[0]['id']), updated_name,
                          updated_description, matchers, updated_group_wait,
                          updated_repeat_interval, {'metricName': 'metric1'},
                          [], [], [])

    @test.attr(type="gate")
    @test.attr(type="negative")
    def test_update_group_rule_definitions_with_no_ok_actions(self):
        matchers = ['alarmName']
        exclusions = {'alarmName': 'alarm1'}
        response_body_list = self._create_group_definitions(
            number_of_definitions=1, matchers=matchers,
            exclusions=exclusions)
        # Update group definition
        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_group_wait = '1h5m'
        updated_repeat_interval = '45s'

        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.update_group_definition,
                          str(response_body_list[0]['id']), updated_name,
                          updated_description, matchers, updated_group_wait,
                          updated_repeat_interval, exclusions, None, None)

    @test.attr(type="gate")
    def test_update_group_rule_definitions_update_notifications(self):
        notification_name = data_utils.rand_name('notification-')
        notification_type = 'EMAIL'
        address = 'root@localhost'

        resp, response_body = self.monasca_client.create_notification_method(
            notification_name, type=notification_type, address=address)
        notification_id1 = self._verify_create_notification_method(
            resp, response_body, notification_name, notification_type, address)

        notification_name = data_utils.rand_name('notification-')
        notification_type = 'EMAIL'
        address = 'root@localhost'

        resp, response_body = self.monasca_client.create_notification_method(
            notification_name, type=notification_type, address=address)
        notification_id2 = self._verify_create_notification_method(
            resp, response_body, notification_name, notification_type, address)

        # Create a group definition
        matchers = ['alarmName']
        exclusions = {'alarmName': 'alarm1'}
        response_body_list = self._create_group_definitions(
            number_of_definitions=1, alarm_actions=[notification_id1],
            matchers=matchers, exclusions=exclusions)
        # Update group definition
        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_group_wait = '1h5m'
        updated_repeat_interval = '45s'

        resp, response_body = self.monasca_client.update_group_definition(
            str(response_body_list[0]['id']), updated_name, updated_description,
            matchers, updated_group_wait, updated_repeat_interval,
            exclusions, [notification_id2], [notification_id2],
            [notification_id2])
        self.assertEqual(200, resp.status)
        self._verify_update_patch_group_definition(response_body,
                                                   updated_name,
                                                   updated_description,
                                                   updated_group_wait,
                                                   updated_repeat_interval,
                                                   notification_id2)
        # Validate fields updated
        resp, response_body = self.monasca_client.get_group_definition(
            response_body_list[0]['id'])
        self._verify_update_patch_group_definition(response_body,
                                                   updated_name,
                                                   updated_description,
                                                   updated_group_wait,
                                                   updated_repeat_interval,
                                                   notification_id2)
        links = response_body['links']
        self._verify_list_group_definitions_links(links)

    @test.attr(type="gate")
    @test.attr(type="negative")
    def test_update_group_rule_definitions_with_invalid_id(self):
        def_id = data_utils.rand_name()

        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_matchers = ['metricName']
        updated_exclusions = {'metricName': 'metric1'}
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.update_group_definition,
                          def_id, updated_name, updated_description,
                          updated_matchers, '30s', '1h', updated_exclusions,
                          [], [], [])

    # Patch

    @test.attr(type="gate")
    def test_patch_group_rule_definitions(self):
        matchers = ['alarmName']
        exclusions = {'alarmName': 'alarm1'}
        response_body_list = self._create_group_definitions(
            number_of_definitions=1, matchers=matchers,
            exclusions=exclusions)
        # Patch alarm definition
        resp, response_body = self.monasca_client.patch_group_definition(
            id=response_body_list[0]['id']
        )
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_patch_group_rule_definitions_with_optional_params(self):
        matchers = ['alarmname']
        exclusions = {'alarmname': 'alarm1'}
        response_body_list = self._create_group_definitions(
            number_of_definitions=1, matchers=matchers,
            exclusions=exclusions)
        # patch alarm definition
        patched_name = data_utils.rand_name('patched_name')
        patched_description = 'updated description'
        patched_group_wait = '1h5m'
        patched_repeat_interval = '45s'
        resp, response_body = self.monasca_client.patch_group_definition(
            id=response_body_list[0]['id'],
            name=patched_name,
            description=patched_description,
            group_wait=patched_group_wait,
            repeat_interval=patched_repeat_interval
        )
        self.assertEqual(200, resp.status)
        self._verify_update_patch_group_definition(response_body,
                                                   patched_name,
                                                   patched_description,
                                                   patched_group_wait,
                                                   patched_repeat_interval,
                                                   None)
        # validate fields updated
        resp, response_body = self.monasca_client.get_group_definition(
            response_body_list[0]['id'])
        self._verify_update_patch_group_definition(response_body,
                                                   patched_name,
                                                   patched_description,
                                                   patched_group_wait,
                                                   patched_repeat_interval,
                                                   None)

    @test.attr(type="gate")
    @test.attr(type="negative")
    def test_patch_group_rule_definitions_with_matchers_or_exclusions(self):
        matchers = ['alarmName']
        exclusions = {'alarmName': 'alarm1'}
        response_body_list = self._create_group_definitions(
            number_of_definitions=1, matchers=matchers,
            exclusions=exclusions)
        # Update group definition
        patched_name = data_utils.rand_name('updated_name')
        patched_description = 'updated description'
        patched_group_wait = '1h5m'
        patched_repeat_interval = '45s'

        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.patch_group_definition,
                          str(response_body_list[0]['id']), patched_name,
                          patched_description, ['metricName'],
                          patched_group_wait, patched_repeat_interval,
                          exclusions, [], [], [])

        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.update_group_definition,
                          str(response_body_list[0]['id']), patched_name,
                          patched_description, matchers, patched_group_wait,
                          patched_repeat_interval, {'metricName': 'metric1'},
                          [], [], [])

    @test.attr(type="gate")
    def test_patch_group_rule_definitions_actions(self):
        notification_name = data_utils.rand_name('notification-')
        notification_type = 'EMAIL'
        address = 'root@localhost'

        resp, response_body = self.monasca_client.create_notification_method(
            notification_name, type=notification_type, address=address)
        notification_id = self._verify_create_notification_method(
            resp, response_body, notification_name, notification_type, address)

        response_body_list = self._create_group_definitions(
            number_of_definitions=1)

        # patch alarm definition
        resp, response_body = self.monasca_client.patch_group_definition(
            id=response_body_list[0]['id'],
            alarm_actions=[notification_id],
            ok_actions=[notification_id],
            undetermined_actions=[notification_id]
        )
        self.assertEqual(200, resp.status)
        self._verify_update_patch_group_definition(response_body, None, None,
                                                   None, None,
                                                   notification_id)

        # validate fields updated
        resp, response_body = self.monasca_client.get_group_definition(
            response_body_list[0]['id'])
        self._verify_update_patch_group_definition(response_body, None, None,
                                                   None, None,
                                                   notification_id)

    @test.attr(type="gate")
    @test.attr(type="negative")
    def test_patch_group_rule_definitions_with_invalid_actions(self):
        response_body_list = self._create_group_definitions(
            number_of_definitions=1)
        # Patch alarm definition
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.patch_group_definition,
                          id=response_body_list[0]['id'],
                          alarm_actions=['bad_notification_id'])

        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.patch_group_definition,
                          id=response_body_list[0]['id'],
                          ok_actions=['bad_notification_id'])

        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.patch_group_definition,
                          id=response_body_list[0]['id'],
                          undetermined_actions=['bad_notification_id'])

    @test.attr(type="gate")
    @test.attr(type="negative")
    def test_patch_group_rule_definitions_with_invalid_id(self):
        def_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.patch_group_definition,
                          id=def_id, name='Test')

    # Delete

    @test.attr(type="gate")
    def test_delete_group_rule_definitions(self):
        response_body_list = self._create_group_definitions(
            number_of_definitions=1)
        # Delete alarm definitions
        resp, response_body = self.monasca_client.list_group_definitions()
        self._verify_list_group_definitions_response_body(resp, response_body)
        elements = response_body['elements']
        for element in elements:
            if element['id'] == response_body_list[0]['id']:
                resp, body = self.monasca_client.delete_group_definition(
                    response_body_list[0]['id'])
                self.assertEqual(204, resp.status)
                self.assertRaises(exceptions.NotFound,
                                  self.monasca_client.get_group_definition,
                                  response_body_list[0]['id'])
                return
        self.fail("Failed test_create_and_delete_alarm_definition: "
                  "cannot find the alarm definition just created.")

    @test.attr(type="gate")
    @test.attr(type="negative")
    def test_delete_group_rule_definitions_with_invalid_id(self):
        def_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.delete_group_definition, def_id)

    def _verify_create_group_definitions(self,
                                         resp,
                                         response_body,
                                         group_rule_definition):
        self.assertEqual(201, resp.status)
        self.assertEqual(group_rule_definition['name'], response_body['name'])

        self.assertEqual(group_rule_definition['matchers'],
                         response_body['matchers'])

        if 'description' in group_rule_definition:
            self.assertEqual(group_rule_definition['description'],
                             response_body['description'])
        else:
            self.assertEqual('', response_body['description'])

        if 'exclusions' in group_rule_definition:
            self.assertEqual(group_rule_definition['exclusions'],
                             response_body['exclusions'])
        else:
            self.assertEqual({}, response_body['exclusions'])

        if 'group_wait' in group_rule_definition:
            self.assertEqual(group_rule_definition['group_wait'],
                             response_body['group_wait'])
        else:
            self.assertEqual('30s', response_body['group_wait'])

        if 'repeat_interval' in group_rule_definition:
            self.assertEqual(group_rule_definition['repeat_interval'],
                             str(response_body['repeat_interval']))
        else:
            self.assertEqual('2h', str(response_body['repeat_interval']))

        if 'alarm_actions' in group_rule_definition:
            self.assertEqual(group_rule_definition['alarm_actions'],
                             response_body['alarm_actions'])
        else:
            self.assertEqual([], response_body['alarm_actions'])

        if 'ok_actions' in group_rule_definition:
            self.assertEqual(group_rule_definition['ok_actions'],
                             response_body['ok_actions'])
        else:
            self.assertEqual([], response_body['ok_actions'])

        if 'undetermined_actions' in group_rule_definition:
            self.assertEqual(group_rule_definition['undetermined_actions'],
                             response_body['undetermined_actions'])
        else:
            self.assertEqual([], response_body['undetermined_actions'])

    def _delete_notification(self, notification_id):
        resp, body = self.monasca_client.delete_notification_method(
            notification_id)
        self.assertEqual(204, resp.status)

    def _verify_create_notification_method(
            self, resp, response_body, test_name, test_type, test_address):
        self.assertEqual(201, resp.status)
        self.assertEqual(test_name, response_body['name'])
        self.assertEqual(test_type, response_body['type'])
        self.assertEqual(test_address, response_body['address'])
        notification_id = response_body['id']
        return notification_id

    def _create_group_definitions(self, number_of_definitions, **kwargs):
        matchers = kwargs.get('matchers', ['alarmName'])
        exclusions = kwargs.get('exclusions', {})
        group_wait = kwargs.get('group_wait', '30s')
        repeat_interval = kwargs.get('repeat_interval', None)
        alarm_actions = kwargs.get('alarm_actions', [])
        ok_actions = kwargs.get('ok_actions', [])
        undetermined_actions = kwargs.get('undetermined_actions', [])

        response_body_list = []
        for i in xrange(number_of_definitions):

            name = kwargs.get('name',
                              data_utils.rand_name('alarm_definition'))
            desc = kwargs.get('description',
                              data_utils.rand_name('description'))

            alarm_definition = helpers.create_group_definition(
                name=name,
                description=desc,
                matchers=matchers,
                exclusions=exclusions,
                group_wait=group_wait,
                repeat_interval=repeat_interval,
                alarm_actions=alarm_actions,
                ok_actions=ok_actions,
                undetermined_actions=undetermined_actions
            )
            resp, response_body = self.monasca_client.create_group_definitions(
                alarm_definition)
            self.assertEqual(201, resp.status)
            response_body_list.append(response_body)
        return response_body_list

    def _verify_list_group_definitions_response_body(self, resp,
                                                     response_body):
        self.assertEqual(200, resp.status)
        self.assertIsInstance(response_body, dict)
        self.assertTrue(set(['links', 'elements']) == set(response_body))

    def _verify_group_definitions_list(self, observed, reference):
        self.assertEqual(len(reference), len(observed))
        for i in xrange(len(reference)):
            self._verify_group_definitions_element(
                reference[i], observed[i])

    def _verify_group_definitions_element(self, response_body,
                                          res_body_create_group_def):
        self.assertEqual(response_body['name'],
                         res_body_create_group_def['name'])
        self.assertEqual(response_body['matchers'],
                         res_body_create_group_def['matchers'])
        self.assertEqual(response_body['id'], res_body_create_group_def['id'])
        self.assertEqual(response_body['description'],
                         res_body_create_group_def['description'])
        self.assertEqual(response_body['group_wait'],
                         res_body_create_group_def['group_wait'])
        self.assertEqual(response_body['repeat_interval'],
                         res_body_create_group_def['repeat_interval'])
        self.assertEqual(response_body['exclusions'],
                         res_body_create_group_def['exclusions'])

    def _verify_element_set(self, element):
        self.assertEqual(set(['id',
                              'links',
                              'name',
                              'description',
                              'matchers',
                              'exclusions',
                              'group_wait',
                              'repeat_interval',
                              'ok_actions',
                              'alarm_actions',
                              'undetermined_actions']),
                         set(element))

    def _verify_list_group_definitions_links(self, links):
        self.assertIsInstance(links, list)
        link = links[0]
        self.assertTrue(set(['rel', 'href']) == set(link))
        self.assertEqual(link['rel'], u'self')

    def _verify_update_patch_group_definition(self,
                                              response_body,
                                              updated_name,
                                              updated_description,
                                              updated_group_wait,
                                              updated_repeat_interval,
                                              notification_id):
        if updated_name:
            self.assertEqual(updated_name, response_body['name'])
        if updated_description:
            self.assertEqual(updated_description, response_body['description'])
        if updated_group_wait:
            self.assertEqual(updated_group_wait, response_body['group_wait'])
        if updated_repeat_interval:
            self.assertEqual(updated_repeat_interval, response_body['repeat_interval'])
        if notification_id:
            self.assertEqual(notification_id,
                             response_body['alarm_actions'][0])
            self.assertEqual(notification_id, response_body['ok_actions'][0])
            self.assertEqual(notification_id,
                             response_body['undetermined_actions'][0])
