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


NUM_INHIBITION_DEFINITIONS = 2


class TestAlarmInhibitionDefinitions(base.BaseMonascaTest):

    # Create

    @test.attr(type="python_only")
    def test_create_inhibition_rule_definition(self):
        # Create a inhibition rule definition
        name = data_utils.rand_name('inhibition_rule_definition')
        source_match = {'severity': 'HIGH'}
        target_match = {'severity': 'LOW'}
        equal = ['name']
        inhibition_definition = helpers.create_inhibition_definition(
            name=name, source_match=source_match,
            target_match=target_match, equal=equal)
        resp, response_body = self.monasca_client.create_inhibition_definitions(
            inhibition_definition)

        self._verify_create_inhibition_definitions(resp, response_body,
                                                   inhibition_definition)

    @test.attr(type="python_only")
    def test_create_inhibition_rule_definition_with_optional_params(self):
        # Create a inhibition rule definition
        name = data_utils.rand_name('inhibition_rule_definition')
        description = data_utils.rand_name('description')
        source_match = {'severity': 'HIGH'}
        target_match = {'severity': 'LOW'}
        equal = ['name']
        exclusions = {'alarmName': 'alarm1'}
        inhibition_definition = helpers.create_inhibition_definition(
            name=name, source_match=source_match, description=description,
            target_match=target_match, equal=equal, exclusions=exclusions)
        resp, response_body = self.monasca_client.create_inhibition_definitions(
            inhibition_definition)

        self._verify_create_inhibition_definitions(resp, response_body,
                                                   inhibition_definition)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_create_inhibition_rule_definition_with_name_exceeds_max_length(self):
        # Create a inhibition rule definition
        name = data_utils.rand_name('inhibition_rule_definition')
        remaining_length = constants.MAX_ALARM_DEFINITION_NAME_LENGTH - len(name) + 1
        name += "x" * remaining_length
        source_match = {'severity': 'HIGH'}
        target_match = {'severity': 'LOW'}
        equal = ['name']
        inhibition_definition = helpers.create_inhibition_definition(
            name=name, source_match=source_match, target_match=target_match,
            equal=equal)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_inhibition_definitions,
                          inhibition_definition)

    # List

    @test.attr(type="python_only")
    def test_list_inhibition_rule_definitions(self):
        source_match = {'severity': 'HIGH'}
        target_match = {'severity': 'LOW'}
        equal = ['name']
        response_body_list = self._create_inhibition_definitions(
            source_match=source_match, target_match=target_match, equal=equal,
            number_of_definitions=1)
        query_param = '?name=' + str(response_body_list[0]['name'])
        resp, response_body = self.monasca_client.list_inhibition_definitions(
            query_param)

        # Test list inhibition definition response body
        self._verify_list_inhibition_definitions_response_body(resp, response_body)
        elements = response_body['elements']
        self._verify_inhibition_definitions_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_inhibition_definitions_links(links)

    @test.attr(type="python_only")
    def test_list_inhibition_rule_definitions_with_multibyte_character(self):
        name = data_utils.rand_name('ｄｅｆｉｎｉｔｉｏｎ').decode('utf8')
        description = 'ｄｅｓｃｒｉｐｔｉｏｎ'.decode('utf8')
        response_body_list = self._create_inhibition_definitions(name=name,
                                                                 description=description,
                                                                 number_of_definitions=1)
        query_param = '?name=' + urlparse.quote(name.encode('utf8'))
        resp, response_body = self.monasca_client.list_inhibition_definitions(
            query_param)

        # Test list inhibition definition response body
        self._verify_list_inhibition_definitions_response_body(resp, response_body)
        elements = response_body['elements']
        self._verify_inhibition_definitions_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_inhibition_definitions_links(links)

    @test.attr(type="python_only")
    def test_list_inhibition_rule_definitions_with_name(self):
        name = data_utils.rand_name('inhibition_definition')
        response_body_list = self._create_inhibition_definitions(name=name,
                                                                 number_of_definitions=1)
        query_param = '?name=' + str(name)
        resp, response_body = self.monasca_client.list_inhibition_definitions(
            query_param)

        # Test list inhibition definition response body
        self._verify_list_inhibition_definitions_response_body(resp, response_body)
        elements = response_body['elements']
        self._verify_inhibition_definitions_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_inhibition_definitions_links(links)

    @test.attr(type="python_only")
    def test_list_inhibition_definitions_with_offset_limit(self):
        helpers.delete_inhibition_definitions(self.monasca_client)
        self._create_inhibition_definitions(
            number_of_definitions=NUM_INHIBITION_DEFINITIONS)
        resp, response_body = self.monasca_client.list_inhibition_definitions()
        self._verify_list_inhibition_definitions_response_body(resp, response_body)
        first_element = response_body['elements'][0]
        last_element = response_body['elements'][1]

        query_parms = '?limit=2'
        resp, response_body = self.monasca_client.list_inhibition_definitions(
            query_parms)
        self.assertEqual(200, resp.status)

        elements = response_body['elements']
        self.assertEqual(2, len(elements))
        self.assertEqual(first_element, elements[0])
        self.assertEqual(last_element, elements[1])

        for offset in xrange(0, 2):
            for limit in xrange(1, 3 - offset):
                query_parms = '?offset=' + str(offset) + '&limit=' + str(limit)
                resp, response_body = self.monasca_client.list_inhibition_definitions(query_parms)
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

    @test.attr(type="python_only")
    def test_get_inhibition_rule_definitions(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        resp, response_body = self.monasca_client.get_inhibition_definition(
            response_body_list[0]['id'])

        self.assertEqual(200, resp.status)
        self._verify_element_set(response_body)
        self._verify_inhibition_definitions_element(response_body,
                                                    response_body_list[0])
        links = response_body['links']
        self._verify_list_inhibition_definitions_links(links)

    @test.attr(type="python_only")
    def test_get_inhibition_rule_definitions_with_multibyte_character(self):
        name = data_utils.rand_name('ｄｅｆｉｎｉｔｉｏｎ').decode('utf8')
        description = 'ｄｅｓｃｒｉｐｔｉｏｎ'.decode('utf8')
        response_body_list = self._create_inhibition_definitions(
            name=name, description=description, number_of_definitions=1)

        resp, response_body = self.monasca_client.get_inhibition_definition(
            response_body_list[0]['id'])

        self.assertEqual(200, resp.status)
        self._verify_element_set(response_body)
        self._verify_inhibition_definitions_element(response_body,
                                                    response_body_list[0])
        links = response_body['links']
        self._verify_list_inhibition_definitions_links(links)

    @test.attr(type="python_only")
    @test.attr(type='negative')
    def test_get_inhibition_defintion_with_invalid_id(self):
        def_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.get_inhibition_definition, def_id)

    # Update

    @test.attr(type="python_only")
    def test_update_inhibition_rule_definitions(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_description = data_utils.rand_name('updated description')
        updated_source_match = {'severity': 'HIGH'}
        updated_target_match = {'severity': 'LOW'}
        updated_equal = ['alarmName']
        updated_exclusions = {}

        resp, response_body = self.monasca_client.update_inhibition_definition(
            str(response_body_list[0]['id']), updated_name, updated_description,
            updated_equal, updated_source_match, updated_target_match,
            updated_exclusions)
        self.assertEqual(200, resp.status)
        self._verify_update_patch_inhibition_definition(response_body, updated_name,
                                                        updated_description, updated_equal,
                                                        updated_source_match,
                                                        updated_target_match, updated_exclusions)
        # Validate fields updated
        resp, response_body = self.monasca_client.get_inhibition_definition(
            response_body_list[0]['id'])
        self._verify_update_patch_inhibition_definition(response_body, updated_name,
                                                        updated_description, updated_equal,
                                                        updated_source_match,
                                                        updated_target_match, updated_exclusions)
        links = response_body['links']
        self._verify_list_inhibition_definitions_links(links)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_update_inhibition_rule_definitions_with_different_source_match(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_description = data_utils.rand_name('updated description')
        updated_source_match = {'severity': 'CRITICAL'}
        updated_target_match = {'severity': 'LOW'}
        updated_equal = ['alarmName']
        updated_exclusions = {}

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.update_inhibition_definition,
            str(response_body_list[0]['id']), updated_name, updated_description,
            updated_equal, updated_source_match, updated_target_match,
            updated_exclusions)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_update_inhibition_rule_definitions_with_different_target_match(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_description = data_utils.rand_name('updated description')
        updated_source_match = {'severity': 'HIGH'}
        updated_target_match = {'severity': 'CRITICAL'}
        updated_equal = ['alarmName']
        updated_exclusions = {}

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.update_inhibition_definition,
            str(response_body_list[0]['id']), updated_name, updated_description,
            updated_equal, updated_source_match, updated_target_match,
            updated_exclusions)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_update_inhibition_rule_definitions_with_different_equal(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_description = data_utils.rand_name('updated description')
        updated_source_match = {'severity': 'HIGH'}
        updated_target_match = {'severity': 'LOW'}
        updated_equal = ['metricName']
        updated_exclusions = {}

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.update_inhibition_definition,
            str(response_body_list[0]['id']), updated_name, updated_description,
            updated_equal, updated_source_match, updated_target_match,
            updated_exclusions)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_update_inhibition_rule_definitions_with_different_exclusions(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_description = data_utils.rand_name('updated description')
        updated_source_match = {'severity': 'HIGH'}
        updated_target_match = {'severity': 'LOW'}
        updated_equal = ['alarmName']
        updated_exclusions = {"alarmName": "test_alarm1"}

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.update_inhibition_definition,
            str(response_body_list[0]['id']), updated_name, updated_description,
            updated_equal, updated_source_match, updated_target_match,
            updated_exclusions)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_update_inhibition_rule_definitions_with_no_exlcusions(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_description = data_utils.rand_name('updated description')
        updated_source_match = {'severity': 'HIGH'}
        updated_target_match = {'severity': 'LOW'}
        updated_equal = ['alarmName']

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.update_inhibition_definition,
            str(response_body_list[0]['id']), updated_name, updated_description,
            updated_equal, updated_source_match, updated_target_match)

    @test.attr(type="python_only")
    @test.attr(type='negative')
    def test_update_inhibition_defintion_with_invalid_id(self):
        def_id = data_utils.rand_name()

        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_source_match = {'severity': 'HIGH'}
        updated_target_match = {'severity': 'LOW'}
        updated_equal = ['alarmName']
        updated_exclusions = {"alarmName": "test_alarm1"}
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.update_inhibition_definition,
                          def_id, updated_name, updated_description,
                          updated_equal, updated_source_match, updated_target_match,
                          updated_exclusions)

    # Patch

    @test.attr(type="python_only")
    def test_patch_inhibition_rule_definitions(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_description = data_utils.rand_name('updated description')

        resp, response_body = self.monasca_client.patch_inhibition_definition(
            str(response_body_list[0]['id']), updated_name, updated_description)
        self.assertEqual(200, resp.status)
        self._verify_update_patch_inhibition_definition(response_body, updated_name,
                                                        updated_description, None, None,
                                                        None, None)
        # Validate fields updated
        resp, response_body = self.monasca_client.get_inhibition_definition(
            response_body_list[0]['id'])
        self._verify_update_patch_inhibition_definition(response_body, updated_name,
                                                        updated_description, None, None,
                                                        None, None)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_patch_inhibition_rule_definitions_with_different_source_match(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_source_match = {'severity': 'CRITICAL'}

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.patch_inhibition_definition,
            str(response_body_list[0]['id']), updated_name,
            source_match=updated_source_match)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_patch_inhibition_rule_definitions_with_different_target_match(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_target_match = {'severity': 'CRITICAL'}

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.patch_inhibition_definition,
            str(response_body_list[0]['id']), updated_name,
            target_match=updated_target_match)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_patch_inhibition_rule_definitions_with_different_equal(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_equal = ['metricName']

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.patch_inhibition_definition,
            str(response_body_list[0]['id']), updated_name,
            equal=updated_equal)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_patch_inhibition_rule_definitions_with_different_exceptions(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        updated_name = data_utils.rand_name('updated_name')
        updated_exclusions = {"alarmName": "test_alarm1"}

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.patch_inhibition_definition,
            str(response_body_list[0]['id']), updated_name,
            exclusions=updated_exclusions)

    @test.attr(type="python_only")
    @test.attr(type='negative')
    def test_patch_inhibition_defintion_with_invalid_id(self):
        def_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.patch_inhibition_definition,
                          id=def_id, name='Test')

    # Delete

    @test.attr(type="python_only")
    def test_create_and_delete_inhibition_definition(self):
        response_body_list = self._create_inhibition_definitions(
            number_of_definitions=1)
        # Delete inhibition definitions
        resp, response_body = self.monasca_client.list_inhibition_definitions()
        self._verify_list_inhibition_definitions_response_body(resp, response_body)
        elements = response_body['elements']
        for element in elements:
            if element['id'] == response_body_list[0]['id']:
                resp, body = self.monasca_client.delete_inhibition_definition(
                    response_body_list[0]['id'])
                self.assertEqual(204, resp.status)
                self.assertRaises(exceptions.NotFound,
                                  self.monasca_client.get_inhibition_definition,
                                  response_body_list[0]['id'])
                return
        self.fail("Failed test_create_and_delete_inhibition_definition: "
                  "cannot find the inhibition definition just created.")

    @test.attr(type="python_only")
    @test.attr(type='negative')
    def test_delete_inhibition_defintion_with_invalid_id(self):
        def_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.delete_inhibition_definition, def_id)

    # Helpers

    def _verify_create_inhibition_definitions(self, resp, response_body,
                                              inhibition_definition):
        self.assertEqual(201, resp.status)
        self.assertEqual(inhibition_definition['name'], response_body['name'])
        self.assertEqual(inhibition_definition['source_match'],
                         response_body['source_match'])
        self.assertEqual(inhibition_definition['target_match'],
                         response_body['target_match'])
        self.assertEqual(inhibition_definition['equal'],
                         response_body['equal'])

        if 'description' in inhibition_definition:
            self.assertEqual(inhibition_definition['description'],
                             response_body['description'])
        else:
            self.assertEqual('', response_body['description'])

        if 'exclusions' in inhibition_definition:
            self.assertEqual(inhibition_definition['exclusions'],
                             response_body['exclusions'])
        else:
            self.assertEqual({}, response_body['exclusions'])

    def _create_inhibition_definitions(self, number_of_definitions, **kwargs):
        source_match = kwargs.get('source_match', {'severity': 'HIGH'})
        target_match = kwargs.get('target_match', {'severity': 'LOW'})
        equal = kwargs.get('equal', ['alarmName'])
        exclusions = kwargs.get('exclusions', {})
        response_body_list = []
        for i in xrange(number_of_definitions):

            name = kwargs.get('name',
                              data_utils.rand_name('inhibition_definition'))
            desc = kwargs.get('description',
                              data_utils.rand_name('description'))

            inhibition_definition = helpers.create_inhibition_definition(
                name=name,
                description=desc,
                source_match=source_match,
                target_match=target_match,
                equal=equal,
                exclusions=exclusions
            )
            resp, response_body = self.monasca_client.create_inhibition_definitions(
                inhibition_definition)
            self.assertEqual(201, resp.status)
            response_body_list.append(response_body)
        return response_body_list

    def _verify_list_inhibition_definitions_response_body(self, resp,
                                                          response_body):
        self.assertEqual(200, resp.status)
        self.assertIsInstance(response_body, dict)
        self.assertTrue(set(['links', 'elements']) == set(response_body))

    def _verify_inhibition_definitions_list(self, observed, reference):
        self.assertEqual(len(reference), len(observed))
        for i in xrange(len(reference)):
            self._verify_inhibition_definitions_element(
                reference[i], observed[i])

    def _verify_list_inhibition_definitions_links(self, links):
        self.assertIsInstance(links, list)
        link = links[0]
        self.assertTrue(set(['rel', 'href']) == set(link))
        self.assertEqual(link['rel'], u'self')

    def _verify_inhibition_definitions_element(self, response_body,
                                               res_body_create_inhibition_def):
        self._verify_element_set(response_body)
        self.assertEqual(response_body['name'],
                         res_body_create_inhibition_def['name'])
        self.assertEqual(response_body['source_match'],
                         res_body_create_inhibition_def['source_match'])
        self.assertEqual(response_body['target_match'],
                         res_body_create_inhibition_def['target_match'])
        self.assertEqual(response_body['equal'],
                         res_body_create_inhibition_def['equal'])
        self.assertEqual(response_body['description'],
                         res_body_create_inhibition_def['description'])
        self.assertEqual(response_body['exclusions'],
                         res_body_create_inhibition_def['exclusions'])

    def _verify_element_set(self, element):
        self.assertTrue(set(['id',
                             'links',
                             'name',
                             'description',
                             'source_match',
                             'target_match',
                             'exclusions',
                             'equal']) ==
                        set(element))

    def _verify_update_patch_inhibition_definition(self, response_body, updated_name,
                                                   updated_description, updated_equal,
                                                   updated_source_match, updated_target_match,
                                                   updated_exclusions):
        if updated_name is not None:
            self.assertEqual(updated_name, response_body['name'])
        if updated_description is not None:
            self.assertEqual(updated_description, response_body['description'])
        if updated_equal is not None:
            self.assertEqual(updated_equal, response_body['equal'])
        if updated_source_match is not None:
            self.assertEqual(updated_source_match, response_body['source_match'])
        if updated_target_match is not None:
            self.assertEqual(updated_target_match, response_body['target_match'])
        if updated_exclusions is not None:
            self.assertEqual(updated_exclusions, response_body['exclusions'])
