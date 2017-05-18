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
from tempest.lib import decorators
from tempest.lib import exceptions

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import constants
from monasca_tempest_tests.tests.api import helpers


NUM_GROUP_DEFINITIONS = 2


class TestGroupRules(base.BaseMonascaTest):

    # Create

    @decorators.attr(type="python_only")
    def test_create_group_rule(self):
        # Create a group rule
        name = data_utils.rand_name('group_rule')
        expression = "group by hostname, service"
        group_rule = helpers.create_group_rule(
            name=name, expression=expression)
        resp, response_body = self.monasca_client.create_group_rules(
            group_rule)
        self._verify_create_group_rules(resp, response_body, group_rule)

    @decorators.attr(type="python_only")
    def test_create_group_rule_with_notifications(self):
        notification_name = data_utils.rand_name('notification-')
        notification_type = 'EMAIL'
        notification_address = 'root@localhost'
        resp, response_body = self.monasca_client.create_notification_method(
            name=notification_name, type=notification_type,
            address=notification_address)
        notification_id = self._verify_create_notification_method(
            resp, response_body, notification_name, notification_type,
            notification_address)

        # Create a group rule
        name = data_utils.rand_name('group_rule_name')
        expression = "group by hostname, service"
        group_rule = helpers.create_group_rule(
            name=name, expression=expression, alarm_actions=[notification_id],
            ok_actions=[notification_id],
            undetermined_actions=[notification_id])
        resp, response_body = self.monasca_client.create_group_rules(
            group_rule)

        self._verify_create_group_rules(resp, response_body, group_rule)
        self.assertEqual(notification_id, response_body['ok_actions'][0])
        self.assertEqual(notification_id, response_body['alarm_actions'][0])
        self.assertEqual(notification_id,
                         response_body['undetermined_actions'][0])

        self._delete_notification(notification_id)

    @decorators.attr(type="python_only")
    def test_create_group_rule_with_multiple_notifications(self):
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

        # Create a group rule
        name = data_utils.rand_name('group_rule')
        expression = "group by hostname, service"
        group_rule = helpers.create_group_rule(
            name=name, expression=expression,
            alarm_actions=[notification_id1, notification_id2],
            ok_actions=[notification_id1, notification_id2],
            undetermined_actions=[notification_id1, notification_id2])
        resp, response_body = self.monasca_client.create_group_rules(
            group_rule)

        self._verify_create_group_rules(resp, response_body, group_rule)

        self._delete_notification(notification_id1)
        self._delete_notification(notification_id2)

    @decorators.attr(type="python_only")
    def test_create_group_rule_with_optional_params(self):
        notification_name = data_utils.rand_name('notification-')
        notification_type = 'EMAIL'
        notification_address = 'root@localhost'
        resp, response_body = self.monasca_client.create_notification_method(
            name=notification_name, type=notification_type,
            address=notification_address)
        notification_id = self._verify_create_notification_method(
            resp, response_body, notification_name, notification_type,
            notification_address)

        # Create a group rule
        name = data_utils.rand_name('group_rule')
        expression = "group by hostname, service"
        group_wait = '1d2h5m30s'
        repeat_interval = '2d3h10m45s'
        description = "group rule description"
        group_rule = helpers.create_group_rule(
            name=name, expression=expression, alarm_actions=[notification_id],
            ok_actions=[notification_id], repeat_interval=repeat_interval,
            undetermined_actions=[notification_id], group_wait=group_wait,
            description=description)
        resp, response_body = self.monasca_client.create_group_rules(
            group_rule)

        self._verify_create_group_rules(resp, response_body, group_rule)

        self._delete_notification(notification_id)

    @decorators.attr(type=['negative'])
    @decorators.attr(type="python_only")
    def test_create_group_rule_with_name_exceeds_max_length(self):
        long_name = "x" * (constants.MAX_RULE_NAME_LENGTH + 1)
        expression = "group by hostname, service"
        group_rule = helpers.create_group_rule(name=long_name,
                                               expression=expression)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_group_rules,
                          group_rule)

    @decorators.attr(type=['negative'])
    @decorators.attr(type="python_only")
    def test_create_group_rule_with_description_exceeds_max_length(self):
        name = data_utils.rand_name('group_rule')
        long_description = "x" * (constants.MAX_RULE_DESCRIPTION_LENGTH + 1)
        expression = "group by hostname, service"
        group_rule = helpers.create_group_rule(
            name=name, description=long_description, expression=expression)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_group_rules,
                          group_rule)

    @decorators.attr(type=['negative'])
    @decorators.attr(type="python_only")
    def test_create_group_rule_with_expression_exceeds_max_length(
            self):
        name = data_utils.rand_name('group_rule')
        expression = "x" * (constants.MAX_RULE_EXPRESSION_LENGTH + 1)
        group_rule = helpers.create_group_rule(
            name=name,
            expression=expression)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_group_rules,
                          group_rule)

    @decorators.attr(type=['negative'])
    @decorators.attr(type="python_only")
    def test_create_group_rule_with_alarm_actions_exceeds_max_length(
            self):
        name = data_utils.rand_name('group_rule')
        expression = "group by hostname, service"
        alarm_actions = ["x" * (constants.MAX_RULE_ACTIONS_LENGTH + 1)]
        group_rule = helpers.create_group_rule(
            name=name,
            expression=expression,
            alarm_actions=alarm_actions)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_group_rules,
                          group_rule)

    @decorators.attr(type=['negative'])
    @decorators.attr(type="python_only")
    def test_create_group_rule_with_ok_actions_exceeds_max_length(
            self):
        name = data_utils.rand_name('group_rule')
        expression = "group by hostname, service"
        ok_actions = ["x" * (constants.MAX_RULE_ACTIONS_LENGTH + 1)]
        group_rule = helpers.create_group_rule(
            name=name,
            expression=expression,
            ok_actions=ok_actions)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_group_rules,
                          group_rule)

    @decorators.attr(type=['negative'])
    @decorators.attr(type="python_only")
    def test_create_group_rule_with_undeterm_actions_exceeds_max_length(
            self):
        name = data_utils.rand_name('group_rule')
        expression = "group by hostname, service"
        undetermined_actions = ["x" * (constants.MAX_RULE_ACTIONS_LENGTH + 1)]
        group_rule = helpers.create_group_rule(
            name=name,
            expression=expression,
            undetermined_actions=undetermined_actions)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_group_rules,
                          group_rule)

    # List

    @decorators.attr(type="python_only")
    def test_list_group_rules(self):
        expression = "group by hostname, service"
        response_body_list = self._create_group_rules(
            expression=expression, number_of_rules=1)
        query_param = '?name=' + str(response_body_list[0]['name'])
        resp, response_body = self.monasca_client.list_group_rules(
            query_param)

        # Test list group rule response body
        self._verify_list_group_rules_response_body(resp, response_body)

        elements = response_body['elements']
        self._verify_group_rules_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_group_rules_links(links)

    @decorators.attr(type="python_only")
    def test_list_group_rules_with_multibyte_character(self):
        name = data_utils.rand_name('ｄｅｆｉｎｉｔｉｏｎ').decode('utf8')
        description = 'ｄｅｓｃｒｉｐｔｉｏｎ'.decode('utf8')
        expression = "group by hostname, service"
        response_body_list = self._create_group_rules(
            name=name, expression=expression, description=description,
            number_of_rules=1)
        query_param = '?name=' + urlparse.quote(name.encode('utf8'))
        resp, response_body = self.monasca_client.list_group_rules(
            query_param)

        # Test list group rule response body
        self._verify_list_group_rules_response_body(resp, response_body)

        elements = response_body['elements']
        self._verify_group_rules_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_group_rules_links(links)

    @decorators.attr(type="python_only")
    def test_list_group_rules_with_name(self):
        name = data_utils.rand_name('group_rule')
        expression = "group by hostname, service"
        description = data_utils.rand_name('description')
        group_rule = helpers.create_group_rule(
            name=name,
            description=description,
            expression=expression)
        resp_create, response_body_create = self.monasca_client.\
            create_group_rules(group_rule)
        self.assertEqual(201, resp_create.status)

        query_parms = "?name=" + str(name)
        resp, response_body = self.monasca_client.list_group_rules(
            query_parms)

        # Test list group rule response body
        self._verify_list_group_rules_response_body(resp, response_body)

        elements = response_body['elements']
        self._verify_group_rules_list(elements, [response_body_create])

        links = response_body['links']
        self._verify_list_group_rules_links(links)

    @decorators.attr(type="python_only")
    def test_list_group_rules_with_offset_limit(self):
        helpers.delete_group_rules(self.monasca_client)
        expression = "group by hostname, service"
        self._create_group_rules(
            expression=expression, number_of_rules=NUM_GROUP_DEFINITIONS)
        resp, response_body = self.monasca_client.list_group_rules()

        self._verify_list_group_rules_response_body(resp, response_body)
        first_element = response_body['elements'][0]
        last_element = response_body['elements'][1]

        query_parms = '?limit=2'
        resp, response_body = self.monasca_client.list_group_rules(
            query_parms)
        self.assertEqual(200, resp.status)

        elements = response_body['elements']
        self.assertEqual(2, len(elements))
        self.assertEqual(first_element, elements[0])
        self.assertEqual(last_element, elements[1])

        for offset in xrange(0, 2):
            for limit in xrange(1, 3 - offset):
                query_parms = '?offset=' + str(offset) + '&limit=' + str(limit)
                resp, response_body = self.monasca_client.list_group_rules(query_parms)
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

    @decorators.attr(type="python_only")
    def test_get_group_rules(self):
        create_response_body_list = self._create_group_rules(
            number_of_rules=1)
        resp, get_response_body = self.monasca_client.get_group_rule(
            create_response_body_list[0]['id'])
        self.assertEqual(200, resp.status)
        self._verify_element_set(get_response_body)
        self._verify_group_rules_element(get_response_body,
                                         create_response_body_list[0])
        links = get_response_body['links']
        self._verify_list_group_rules_links(links)

    @decorators.attr(type="python_only")
    def test_get_group_rules_with_multibyte_character(self):
        name = data_utils.rand_name('ｄｅｆｉｎｉｔｉｏｎ').decode('utf8')
        description = 'ｄｅｓｃｒｉｐｔｉｏｎ'.decode('utf8')
        expression = "group by hostname, service"
        response_body_list = self._create_group_rules(
            name=name,
            expression=expression,
            description=description,
            number_of_rules=1)
        group_rule = response_body_list[0]

        resp, response_body = self.monasca_client.get_group_rule(
            group_rule['id'])

        self.assertEqual(200, resp.status)
        self._verify_element_set(response_body)
        self._verify_group_rules_element(response_body, group_rule)
        links = response_body['links']
        self._verify_list_group_rules_links(links)

    @decorators.attr(type="negative")
    @decorators.attr(type="python_only")
    def test_get_group_rules_with_invalid_id(self):
        rule_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.get_group_rule, rule_id)

    # Update

    @decorators.attr(type="python_only")
    def test_update_group_rules(self):
        notification_name = data_utils.rand_name('notification-')
        notification_type = 'EMAIL'
        address = 'root@localhost'

        resp, response_body = self.monasca_client.create_notification_method(
            notification_name, type=notification_type, address=address)
        notification_id = self._verify_create_notification_method(
            resp, response_body, notification_name, notification_type, address)

        expression = "group by hostname, service"

        response_body_list = self._create_group_rules(
            number_of_rules=1, expression=expression)
        # Update group rule
        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_group_wait = '1h5m'
        updated_repeat_interval = '45s'

        resp, response_body = self.monasca_client.update_group_rule(
            str(response_body_list[0]['id']), updated_name, expression,
            updated_description, updated_group_wait, updated_repeat_interval,
            [notification_id], [notification_id], [notification_id])
        self.assertEqual(200, resp.status)
        self._verify_update_patch_group_rule(response_body, updated_name, updated_description,
                                             updated_group_wait, updated_repeat_interval,
                                             notification_id)
        # Validate fields updated
        resp, response_body = self.monasca_client.get_group_rule(
            response_body_list[0]['id'])
        self._verify_update_patch_group_rule(response_body, updated_name, updated_description,
                                             updated_group_wait, updated_repeat_interval,
                                             notification_id)
        links = response_body['links']
        self._verify_list_group_rules_links(links)

    @decorators.attr(type="negative")
    @decorators.attr(type="python_only")
    def test_update_group_rules_with_expression(self):

        # Update group rule
        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_group_wait = '1h5m'
        updated_repeat_interval = '45s'
        expression = "group by hostname, service"
        updated_expression = expression + 'updated'
        response_body_list = self._create_group_rules(
            number_of_rules=1, expression=expression)

        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.update_group_rule,
                          str(response_body_list[0]['id']), updated_name,
                          updated_expression, updated_description, updated_group_wait,
                          updated_repeat_interval,
                          [], [], [])

    @decorators.attr(type="negative")
    @decorators.attr(type="python_only")
    def test_update_group_rules_with_no_ok_actions(self):
        expression = "group by hostname, service"
        response_body_list = self._create_group_rules(
            number_of_rules=1, expression=expression)
        # Update group rule
        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_group_wait = '1h5m'
        updated_repeat_interval = '45s'

        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.update_group_rule_with_no_ok_actions,
                          str(response_body_list[0]['id']), updated_name,
                          expression, updated_description, updated_group_wait,
                          updated_repeat_interval, None, None)

    @decorators.attr(type="python_only")
    def test_update_group_rules_with_notifications(self):
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

        # Create a group rule
        expression = "group by hostname, service"
        response_body_list = self._create_group_rules(
            number_of_rules=1, alarm_actions=[notification_id1],
            expression=expression)
        # Update group rule
        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_group_wait = '1h5m'
        updated_repeat_interval = '45s'

        resp, response_body = self.monasca_client.update_group_rule(
            str(response_body_list[0]['id']), updated_name, expression,
            updated_description, updated_group_wait, updated_repeat_interval,
            [notification_id2], [notification_id2], [notification_id2])
        self.assertEqual(200, resp.status)
        self._verify_update_patch_group_rule(response_body,
                                             updated_name,
                                             updated_description,
                                             updated_group_wait,
                                             updated_repeat_interval,
                                             notification_id2)
        # Validate fields updated
        resp, response_body = self.monasca_client.get_group_rule(
            response_body_list[0]['id'])
        self._verify_update_patch_group_rule(response_body,
                                             updated_name,
                                             updated_description,
                                             updated_group_wait,
                                             updated_repeat_interval,
                                             notification_id2)
        links = response_body['links']
        self._verify_list_group_rules_links(links)

    @decorators.attr(type="negative")
    @decorators.attr(type="python_only")
    def test_update_group_rules_with_invalid_id(self):
        id = data_utils.rand_name()

        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_expression = "group by hostname, service"
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.update_group_rule,
                          id, updated_name, updated_expression,
                          updated_description, '30s', '1h', [], [], [])

    # Patch

    @decorators.attr(type="python_only")
    def test_patch_group_rules(self):
        expression = "group by hostname, service"
        response_body_list = self._create_group_rules(
            number_of_rules=1, expression=expression)
        # Patch group rule
        resp, response_body = self.monasca_client.patch_group_rule(
            response_body_list[0]['id'])
        self.assertEqual(200, resp.status)

    @decorators.attr(type="python_only")
    def test_patch_group_rules_with_optional_params(self):
        expression = "group by hostname, service"
        response_body_list = self._create_group_rules(
            number_of_rules=1, expression=expression)
        # patch group rule
        patched_name = data_utils.rand_name('patched_name')
        patched_description = 'updated description'
        patched_group_wait = '1h5m'
        patched_repeat_interval = '45s'
        resp, patched_response_body = self.monasca_client.patch_group_rule(
            response_body_list[0]['id'],
            name=patched_name,
            description=patched_description,
            group_wait=patched_group_wait,
            repeat_interval=patched_repeat_interval
        )
        self.assertEqual(200, resp.status)
        self._verify_update_patch_group_rule(patched_response_body,
                                             patched_name,
                                             patched_description,
                                             patched_group_wait,
                                             patched_repeat_interval,
                                             None)
        # validate fields updated
        resp, response_body = self.monasca_client.get_group_rule(
            response_body_list[0]['id'])
        self._verify_update_patch_group_rule(response_body,
                                             patched_name,
                                             patched_description,
                                             patched_group_wait,
                                             patched_repeat_interval,
                                             None)

    @decorators.attr(type="negative")
    @decorators.attr(type="python_only")
    def test_patch_group_rules_with_expression(self):
        expression = "group by hostname, service"
        response_body_list = self._create_group_rules(
            number_of_rules=1, expression=expression)
        # patch group rule
        patched_expression = "group by hostname_patched, service_patched"
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.patch_group_rule,
                          str(response_body_list[0]['id']),
                          expression=patched_expression)

    @decorators.attr(type="python_only")
    def test_patch_group_rules_actions(self):
        notification_name = data_utils.rand_name('notification-')
        notification_type = 'EMAIL'
        address = 'root@localhost'

        resp, response_body = self.monasca_client.create_notification_method(
            notification_name, type=notification_type, address=address)
        notification_id = self._verify_create_notification_method(
            resp, response_body, notification_name, notification_type, address)

        response_body_list = self._create_group_rules(number_of_rules=1)

        # patch group rule
        new_name = data_utils.rand_name('new_group_rule_name')
        resp, response_body = self.monasca_client.patch_group_rule(
            response_body_list[0]['id'],
            name=new_name,
            alarm_actions=[notification_id],
            ok_actions=[notification_id],
            undetermined_actions=[notification_id]
        )
        self.assertEqual(200, resp.status)

        self._verify_update_patch_group_rule(response_body, new_name, None, None,
                                             None, notification_id)
        # validate fields updated
        resp, get_response_body = self.monasca_client.get_group_rule(
            response_body_list[0]['id'])
        self._verify_update_patch_group_rule(get_response_body, new_name, None,
                                             None, None, notification_id)

    @decorators.attr(type="negative")
    @decorators.attr(type="python_only")
    def test_patch_group_rules_with_invalid_actions(self):
        response_body_list = self._create_group_rules(
            number_of_rules=1)
        # Patch group rule
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.patch_group_rule,
                          response_body_list[0]['id'],
                          alarm_actions=['bad_notification_id'])

        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.patch_group_rule,
                          response_body_list[0]['id'],
                          ok_actions=['bad_notification_id'])

        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.patch_group_rule,
                          response_body_list[0]['id'],
                          undetermined_actions=['bad_notification_id'])

    @decorators.attr(type="negative")
    @decorators.attr(type="python_only")
    def test_patch_group_rules_with_invalid_id(self):
        rule_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.patch_group_rule,
                          rule_id, name='Test')

    # Delete

    @decorators.attr(type="python_only")
    def test_delete_group_rules(self):
        response_body_list = self._create_group_rules(
            number_of_rules=1)
        # Delete group rules
        resp, response_body = self.monasca_client.list_group_rules()
        self._verify_list_group_rules_response_body(resp, response_body)
        elements = response_body['elements']
        for element in elements:
            if element['id'] == response_body_list[0]['id']:
                resp, body = self.monasca_client.delete_group_rule(
                    response_body_list[0]['id'])
                self.assertEqual(204, resp.status)
                self.assertRaises(exceptions.NotFound,
                                  self.monasca_client.get_group_rule,
                                  response_body_list[0]['id'])
                return
        self.fail("Failed test_create_and_delete_group_rule: "
                  "cannot find the group rule just created.")

    @decorators.attr(type="negative")
    @decorators.attr(type="python_only")
    def test_delete_group_rules_with_invalid_id(self):
        rule_id = data_utils.rand_name('invalid-rule-id')
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.delete_group_rule, rule_id)

    def _verify_create_group_rules(self, resp, response_body, group_rule):
        self.assertEqual(201, resp.status)
        self.assertEqual(group_rule['name'], response_body['name'])

        self.assertEqual(group_rule['expression'], response_body['expression'])

        if 'description' in group_rule:
            self.assertEqual(group_rule['description'],
                             response_body['description'])
        else:
            self.assertEqual('', response_body['description'])

        if 'group_wait' in group_rule:
            self.assertEqual(group_rule['group_wait'], response_body['group_wait'])
        else:
            self.assertEqual('30s', response_body['group_wait'])

        if 'repeat_interval' in group_rule:
            self.assertEqual(group_rule['repeat_interval'],
                             str(response_body['repeat_interval']))
        else:
            self.assertEqual('2h', str(response_body['repeat_interval']))

        if 'alarm_actions' in group_rule:
            self.assertEqual(group_rule['alarm_actions'],
                             response_body['alarm_actions'])
        else:
            self.assertEqual([], response_body['alarm_actions'])

        if 'ok_actions' in group_rule:
            self.assertEqual(group_rule['ok_actions'],
                             response_body['ok_actions'])
        else:
            self.assertEqual([], response_body['ok_actions'])

        if 'undetermined_actions' in group_rule:
            self.assertEqual(group_rule['undetermined_actions'],
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

    def _create_group_rules(self, number_of_rules, **kwargs):
        expression = kwargs.get('expression', "group by hostname, service")
        group_wait = kwargs.get('group_wait', '30s')
        repeat_interval = kwargs.get('repeat_interval', None)
        alarm_actions = kwargs.get('alarm_actions', [])
        ok_actions = kwargs.get('ok_actions', [])
        undetermined_actions = kwargs.get('undetermined_actions', [])

        response_body_list = []
        for i in xrange(number_of_rules):

            name = kwargs.get('name',
                              data_utils.rand_name('group_rule_name'))
            description = kwargs.get('description',
                                     data_utils.rand_name('description'))

            group_rule = helpers.create_group_rule(
                name=name,
                description=description,
                expression=expression,
                group_wait=group_wait,
                repeat_interval=repeat_interval,
                alarm_actions=alarm_actions,
                ok_actions=ok_actions,
                undetermined_actions=undetermined_actions
            )
            resp, response_body = self.monasca_client.create_group_rules(group_rule)
            self.assertEqual(201, resp.status)
            response_body_list.append(response_body)
        return response_body_list

    def _verify_list_group_rules_response_body(self, resp, response_body):
        self.assertEqual(200, resp.status)
        self.assertIsInstance(response_body, dict)
        self.assertTrue(set(['links', 'elements']) == set(response_body))

    def _verify_group_rules_list(self, observed, reference):
        self.assertEqual(len(reference), len(observed))
        for i in xrange(len(reference)):
            self._verify_group_rules_element(reference[i], observed[i])

    def _verify_group_rules_element(self, response_body,
                                    res_body_create_group_rule):
        self.assertEqual(response_body['name'],
                         res_body_create_group_rule['name'])
        self.assertEqual(response_body['expression'],
                         res_body_create_group_rule['expression'])
        self.assertEqual(response_body['id'], res_body_create_group_rule['id'])
        self.assertEqual(response_body['description'],
                         res_body_create_group_rule['description'])
        self.assertEqual(response_body['group_wait'],
                         res_body_create_group_rule['group_wait'])
        self.assertEqual(response_body['repeat_interval'],
                         res_body_create_group_rule['repeat_interval'])

    def _verify_element_set(self, element):
        self.assertEqual(set(['id',
                              'links',
                              'name',
                              'expression',
                              'description',
                              'group_wait',
                              'repeat_interval',
                              'ok_actions',
                              'alarm_actions',
                              'undetermined_actions']),
                         set(element))

    def _verify_list_group_rules_links(self, links):
        self.assertIsInstance(links, list)
        link = links[0]
        self.assertTrue(set(['rel', 'href']) == set(link))
        self.assertEqual(link['rel'], u'self')

    def _verify_update_patch_group_rule(self, response_body, new_name,
                                        new_description, new_group_wait,
                                        new_repeat_interval, notification_id):
        if new_name:
            self.assertEqual(new_name, response_body['name'])
        if new_description:
            self.assertEqual(new_description, response_body['description'])
        if new_group_wait:
            self.assertEqual(new_group_wait, response_body['group_wait'])
        if new_repeat_interval:
            self.assertEqual(new_repeat_interval, response_body['repeat_interval'])
        if notification_id:
            self.assertEqual(notification_id,
                             response_body['alarm_actions'][0])
            self.assertEqual(notification_id, response_body['ok_actions'][0])
            self.assertEqual(notification_id,
                             response_body['undetermined_actions'][0])
