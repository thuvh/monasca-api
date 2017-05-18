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


NUM_INHIBITION_DEFINITIONS = 2


class TestInhibitRules(base.BaseMonascaTest):

    # Create

    @decorators.attr(type="python_only")
    def test_create_inhibit_rule(self):
        # Create a inhibit rule
        name = data_utils.rand_name('inhibit_rule')
        expression = 'source metric_1 targets metric_2 excluding metric_3'
        inhibit_rule = helpers.create_inhibit_rule(
            name=name, expression=expression)
        resp, response_body = self.monasca_client.create_inhibit_rules(
            inhibit_rule)

        self._verify_create_inhibit_rules(resp, response_body, inhibit_rule)

    @decorators.attr(type="python_only")
    def test_create_inhibit_rule_with_optional_params(self):
        # Create a inhibit rule
        name = data_utils.rand_name('inhibit_rule')
        description = data_utils.rand_name('description')
        expression = 'source metric_1 targets metric_2 excluding metric_3'
        inhibit_rule = helpers.create_inhibit_rule(
            name=name, description=description, expression=expression)
        resp, response_body = self.monasca_client.create_inhibit_rules(
            inhibit_rule)

        self._verify_create_inhibit_rules(resp, response_body, inhibit_rule)

    @decorators.attr(type="python_only")
    @decorators.attr(type="negative")
    def test_create_inhibit_rule_with_name_exceeds_max_length(self):
        # Create a inhibit rule
        name = "x" * (constants.MAX_RULE_NAME_LENGTH + 1)
        expression = 'source metric_1 targets metric_2 excluding metric_3'
        inhibit_rule = helpers.create_inhibit_rule(
            name=name, expression=expression)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_inhibit_rules,
                          inhibit_rule)

    @decorators.attr(type="python_only")
    @decorators.attr(type="negative")
    def test_create_inhibit_rule_with_expression_exceeds_max_length(self):
        # Create a inhibit rule
        name = data_utils.rand_name('inhibit_rule_name')
        expression = "x" * (constants.MAX_RULE_EXPRESSION_LENGTH + 1)
        inhibit_rule = helpers.create_inhibit_rule(name=name,
                                                   expression=expression)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_inhibit_rules,
                          inhibit_rule)

    # List

    @decorators.attr(type="python_only")
    def test_list_inhibit_rules(self):
        expression = 'source metric_1 targets metric_2 excluding metric_3'
        response_body_list = self._create_inhibit_rules(expression=expression,
                                                        number_of_rules=1)
        query_param = '?name=' + str(response_body_list[0]['name'])
        resp, response_body = self.monasca_client.list_inhibit_rules(
            query_param)

        # Test list inhibit rule response body
        self._verify_list_inhibit_rules_response_body(resp, response_body)
        elements = response_body['elements']
        self._verify_inhibit_rules_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_inhibit_rules_links(links)

    @decorators.attr(type="python_only")
    def test_list_inhibit_rules_with_multibyte_character(self):
        name = data_utils.rand_name('ｄｅｆｉｎｉｔｉｏｎ').decode('utf8')
        description = 'ｄｅｓｃｒｉｐｔｉｏｎ'.decode('utf8')
        response_body_list = self._create_inhibit_rules(name=name,
                                                        description=description,
                                                        number_of_rules=1)
        query_param = '?name=' + urlparse.quote(name.encode('utf8'))
        resp, response_body = self.monasca_client.list_inhibit_rules(
            query_param)

        # Test list inhibit rule response body
        self._verify_list_inhibit_rules_response_body(resp, response_body)
        elements = response_body['elements']
        self._verify_inhibit_rules_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_inhibit_rules_links(links)

    @decorators.attr(type="python_only")
    def test_list_inhibit_rules_with_name(self):
        name = data_utils.rand_name('inhibit_rule_name')
        response_body_list = self._create_inhibit_rules(name=name, number_of_rules=1)
        query_param = '?name=' + str(name)
        resp, response_body = self.monasca_client.list_inhibit_rules(
            query_param)

        # Test list inhibit rule response body
        self._verify_list_inhibit_rules_response_body(resp, response_body)
        elements = response_body['elements']
        self._verify_inhibit_rules_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_inhibit_rules_links(links)

    @decorators.attr(type="python_only")
    def test_list_inhibit_rules_with_offset_limit(self):
        helpers.delete_inhibit_rules(self.monasca_client)
        self._create_inhibit_rules(number_of_rules=NUM_INHIBITION_DEFINITIONS)
        resp, response_body = self.monasca_client.list_inhibit_rules()
        self._verify_list_inhibit_rules_response_body(resp, response_body)
        first_element = response_body['elements'][0]
        last_element = response_body['elements'][1]

        query_parms = '?limit=2'
        resp, response_body = self.monasca_client.list_inhibit_rules(
            query_parms)
        self.assertEqual(200, resp.status)

        elements = response_body['elements']
        self.assertEqual(2, len(elements))
        self.assertEqual(first_element, elements[0])
        self.assertEqual(last_element, elements[1])

        for offset in xrange(0, 2):
            for limit in xrange(1, 3 - offset):
                query_parms = '?offset=' + str(offset) + '&limit=' + str(limit)
                resp, response_body = self.monasca_client.list_inhibit_rules(
                    query_parms)
                self.assertEqual(200, resp.status)
                new_elements = response_body['elements']
                self.assertEqual(limit, len(new_elements))
                self.assertEqual(elements[offset], new_elements[0])
                self.assertEqual(elements[offset + limit - 1],
                                 new_elements[-1])
                links = response_body['links']
                for link in links:
                    if link['rel'] == 'next':
                        next_offset = helpers.get_query_param(link['href'],
                                                              'offset')
                        next_limit = helpers.get_query_param(link['href'],
                                                             'limit')
                        self.assertEqual(str(offset + limit), next_offset)
                        self.assertEqual(str(limit), next_limit)

    # Get

    @decorators.attr(type="python_only")
    def test_get_inhibit_rules(self):
        response_body_list = self._create_inhibit_rules(
            number_of_rules=1)
        resp, response_body = self.monasca_client.get_inhibit_rule(
            response_body_list[0]['id'])

        self.assertEqual(200, resp.status)
        self._verify_element_set(response_body)
        self._verify_inhibit_rules_element(response_body, response_body_list[0])
        links = response_body['links']
        self._verify_list_inhibit_rules_links(links)

    @decorators.attr(type="python_only")
    def test_get_inhibit_rules_with_multibyte_character(self):
        name = data_utils.rand_name('ａｌａｒｍ＿ｄｅｆｉｎｉｔｉｏｎ').decode('utf8')
        description = 'ｄｅｓｃｒｉｐｔｉｏｎ'.decode('utf8')
        response_body_list = self._create_inhibit_rules(
            name=name, description=description, number_of_rules=1)

        resp, response_body = self.monasca_client.get_inhibit_rule(
            response_body_list[0]['id'])

        self.assertEqual(200, resp.status)
        self._verify_element_set(response_body)
        self._verify_inhibit_rules_element(response_body, response_body_list[0])
        links = response_body['links']
        self._verify_list_inhibit_rules_links(links)

    @decorators.attr(type="python_only")
    @decorators.attr(type='negative')
    def test_get_inhibit_rule_with_invalid_id(self):
        def_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.get_inhibit_rule, def_id)

    # Update

    @decorators.attr(type="python_only")
    def test_update_inhibit_rules(self):
        response_body_list = self._create_inhibit_rules(
            number_of_rules=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_description = data_utils.rand_name('updated_description')
        updated_expression = 'source metric_1 targets metric_2 excluding metric_3'

        resp, response_body = self.monasca_client.update_inhibit_rule(
            str(response_body_list[0]['id']), updated_name, updated_expression,
            updated_description)
        self.assertEqual(200, resp.status)
        self._verify_update_patch_inhibit_rule(response_body, updated_name,
                                               updated_expression,
                                               updated_description)
        # Validate fields updated
        resp, response_body = self.monasca_client.get_inhibit_rule(
            response_body_list[0]['id'])
        self._verify_update_patch_inhibit_rule(response_body, updated_name,
                                               updated_expression,
                                               updated_description)
        links = response_body['links']
        self._verify_list_inhibit_rules_links(links)

    @decorators.attr(type="python_only")
    @decorators.attr(type="negative")
    def test_update_inhibit_rules_with_different_expression(self):
        response_body_list = self._create_inhibit_rules(
            number_of_rules=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_description = data_utils.rand_name('updated description')
        updated_expression = "metric1_new target metric2_new"

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.update_inhibit_rule,
            str(response_body_list[0]['id']), updated_name, updated_expression,
            updated_description)

    @decorators.attr(type="python_only")
    @decorators.attr(type='negative')
    def test_update_inhibit_rule_with_invalid_id(self):
        def_id = data_utils.rand_name()

        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_expression = 'source metric_1 targets metric_2 excluding metric_3'
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.update_inhibit_rule,
                          def_id, updated_name, updated_expression, updated_description)

    # Patch

    @decorators.attr(type="python_only")
    def test_patch_inhibit_rules(self):
        response_body_list = self._create_inhibit_rules(
            number_of_rules=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_description = data_utils.rand_name('updated description')

        resp, response_body = self.monasca_client.patch_inhibit_rule(
            str(response_body_list[0]['id']), name=updated_name,
            description=updated_description)
        self.assertEqual(200, resp.status)
        self._verify_update_patch_inhibit_rule(response_body, updated_name,
                                               None, updated_description)
        # Validate fields updated
        resp, response_body = self.monasca_client.get_inhibit_rule(
            response_body_list[0]['id'])
        self._verify_update_patch_inhibit_rule(response_body, updated_name,
                                               None, updated_description)

    @decorators.attr(type="python_only")
    @decorators.attr(type="negative")
    def test_patch_inhibit_rules_with_different_expression(self):
        response_body_list = self._create_inhibit_rules(
            number_of_rules=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_expression = 'source updated_metric_1 targets updated_metric_2' \
                             ' excluding updated_metric_3'

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.patch_inhibit_rule,
            str(response_body_list[0]['id']), name=updated_name,
            expression=updated_expression)

    @decorators.attr(type="python_only")
    @decorators.attr(type='negative')
    def test_patch_inhibit_rule_with_invalid_id(self):
        rule_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.patch_inhibit_rule,
                          rule_id)

    # Delete

    @decorators.attr(type="python_only")
    def test_create_and_delete_inhibit_rule(self):
        response_body_list = self._create_inhibit_rules(number_of_rules=1)
        # Delete inhibit rules
        resp, response_body = self.monasca_client.list_inhibit_rules()
        self._verify_list_inhibit_rules_response_body(resp, response_body)
        elements = response_body['elements']
        for element in elements:
            if element['id'] == response_body_list[0]['id']:
                resp, body = self.monasca_client.delete_inhibit_rule(
                    response_body_list[0]['id'])
                self.assertEqual(204, resp.status)
                self.assertRaises(exceptions.NotFound,
                                  self.monasca_client.get_inhibit_rule,
                                  response_body_list[0]['id'])
                return
        self.fail("Failed test_create_and_delete_inhibit_rule: "
                  "cannot find the inhibit rule just created.")

    @decorators.attr(type="python_only")
    @decorators.attr(type='negative')
    def test_delete_inhibit_rule_with_invalid_id(self):
        def_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.delete_inhibit_rule, def_id)

    # Helpers

    def _verify_create_inhibit_rules(self, resp, response_body, inhibit_rule):
        self.assertEqual(201, resp.status)
        self.assertEqual(inhibit_rule['name'], response_body['name'])
        self.assertEqual(inhibit_rule['expression'],
                         response_body['expression'])

        if 'description' in inhibit_rule:
            self.assertEqual(inhibit_rule['description'],
                             response_body['description'])
        else:
            self.assertEqual('', response_body['description'])

    def _create_inhibit_rules(self, number_of_rules, **kwargs):
        expression = kwargs.get(
            'expression',
            'source metric_1 targets metric_2 excluding metric_3')
        response_body_list = []
        for i in xrange(number_of_rules):

            name = kwargs.get('name',
                              data_utils.rand_name('inhibit_rule_name'))
            description = kwargs.get('description',
                                     data_utils.rand_name('description'))

            inhibit_rule = helpers.create_inhibit_rule(
                name=name,
                expression=expression,
                description=description,
            )
            resp, response_body = self.monasca_client.create_inhibit_rules(
                inhibit_rule)
            self.assertEqual(201, resp.status)
            response_body_list.append(response_body)
        return response_body_list

    def _verify_list_inhibit_rules_response_body(self, resp, response_body):
        self.assertEqual(200, resp.status)
        self.assertIsInstance(response_body, dict)
        self.assertTrue(set(['links', 'elements']) == set(response_body))

    def _verify_inhibit_rules_list(self, observed, reference):
        self.assertEqual(len(reference), len(observed))
        for i in xrange(len(reference)):
            self._verify_inhibit_rules_element(
                reference[i], observed[i])

    def _verify_list_inhibit_rules_links(self, links):
        self.assertIsInstance(links, list)
        link = links[0]
        self.assertTrue(set(['rel', 'href']) == set(link))
        self.assertEqual(link['rel'], u'self')

    def _verify_inhibit_rules_element(self, response_body, res_body_create_inhibit_rule):
        self._verify_element_set(response_body)
        self.assertEqual(response_body['name'],
                         res_body_create_inhibit_rule['name'])
        self.assertEqual(response_body['expression'],
                         res_body_create_inhibit_rule['expression'])
        self.assertEqual(response_body['description'],
                         res_body_create_inhibit_rule['description'])

    def _verify_element_set(self, element):
        self.assertTrue(set(['id',
                             'links',
                             'name',
                             'expression',
                             'description']) ==
                        set(element))

    def _verify_update_patch_inhibit_rule(self, response_body, updated_name,
                                          updated_expression, updated_description):
        if updated_name is not None:
            self.assertEqual(updated_name, response_body['name'])
        if updated_expression is not None:
            self.assertEqual(updated_expression, response_body['expression'])
        if updated_description is not None:
            self.assertEqual(updated_description, response_body['description'])
