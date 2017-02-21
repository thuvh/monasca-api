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

NUM_SILENCE_DEFINITIONS = 2


class TestAlarmSilenceDefinitions(base.BaseMonascaTest):

    # Create

    @test.attr(type="python_only")
    def test_create_silence_rule_definition(self):
        # Create a silence rule definition
        name = data_utils.rand_name('silence_rule_definition')
        matchers = {"silenceName": "testAlarm1"}
        silence_definition = helpers.create_silence_definition(
            name=name, matchers=matchers)
        resp, response_body = self.monasca_client.create_silence_definitions(
            silence_definition)

        self._verify_create_silence_definitions(resp, response_body,
                                                silence_definition)

    @test.attr(type="python_only")
    def test_create_silence_rule_definition_with_optional_params(self):
        # Create a silence rule definition
        name = data_utils.rand_name('silence_rule_definition')
        matchers = {"silenceName": "testAlarm1"}
        description = data_utils.rand_name('description')
        silence_duration = '1h'
        silence_definition = helpers.create_silence_definition(
            name=name, matchers=matchers, description=description,
            silence_duration=silence_duration)
        resp, response_body = self.monasca_client.create_silence_definitions(
            silence_definition)

        self._verify_create_silence_definitions(resp, response_body,
                                                silence_definition)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_create_silence_rule_definition_with_name_exceeds_max_length(self):
        # Create a silence rule definition
        name = data_utils.rand_name('silence_rule_definition')
        remaining_length = constants.MAX_ALARM_DEFINITION_NAME_LENGTH - len(name) + 1
        name += "x" * remaining_length
        matchers = {"silenceName": "testAlarm1"}
        silence_definition = helpers.create_silence_definition(
            name=name, matchers=matchers)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_silence_definitions,
                          silence_definition)

    # List

    @test.attr(type="python_only")
    def test_list_silence_rule_definitions(self):
        response_body_list = self._create_silence_definitions(
            number_of_definitions=1)
        query_param = '?name=' + str(response_body_list[0]['name'])
        resp, response_body = self.monasca_client.list_silence_definitions(
            query_param)

        # Test list silence definition response body
        self._verify_list_silence_definitions_response_body(resp, response_body)
        elements = response_body['elements']
        self._verify_silence_definitions_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_silence_definitions_links(links)

    @test.attr(type="python_only")
    def test_list_silence_rule_definitions_with_multibyte_character(self):
        name = data_utils.rand_name('ｄｅｆｉｎｉｔｉｏｎ').decode('utf8')
        description = 'ｄｅｓｃｒｉｐｔｉｏｎ'.decode('utf8')
        response_body_list = self._create_silence_definitions(
            number_of_definitions=1, name=name, description=description)
        query_param = '?name=' + urlparse.quote(name.encode('utf8'))
        resp, response_body = self.monasca_client.list_silence_definitions(
            query_param)

        # Test list silence definition response body
        self._verify_list_silence_definitions_response_body(resp, response_body)
        elements = response_body['elements']
        self._verify_silence_definitions_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_silence_definitions_links(links)

    @test.attr(type="python_only")
    def test_list_silence_rule_definitions_with_name(self):
        name = data_utils.rand_name('silence_definition')
        response_body_list = self._create_silence_definitions(
            number_of_definitions=1, name=name)
        query_param = '?name=' + str(name)
        resp, response_body = self.monasca_client.list_silence_definitions(
            query_param)

        # Test list silence definition response body
        self._verify_list_silence_definitions_response_body(resp, response_body)
        elements = response_body['elements']
        self._verify_silence_definitions_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_silence_definitions_links(links)

    @test.attr(type="python_only")
    def test_list_silence_definitions_with_offset_limit(self):
        helpers.delete_silence_definitions(self.monasca_client)
        self._create_silence_definitions(
            number_of_definitions=NUM_SILENCE_DEFINITIONS)
        resp, response_body = self.monasca_client.list_silence_definitions()
        self._verify_list_silence_definitions_response_body(resp, response_body)
        first_element = response_body['elements'][0]
        last_element = response_body['elements'][1]

        query_parms = '?limit=2'
        resp, response_body = self.monasca_client.list_silence_definitions(
            query_parms)
        self.assertEqual(200, resp.status)

        elements = response_body['elements']
        self.assertEqual(2, len(elements))
        self.assertEqual(first_element, elements[0])
        self.assertEqual(last_element, elements[1])

        for offset in xrange(0, 2):
            for limit in xrange(1, 3 - offset):
                query_parms = '?offset=' + str(offset) + '&limit=' + str(limit)
                resp, response_body = self.monasca_client.list_silence_definitions(query_parms)
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
    def test_get_silence_rule_definitions(self):
        response_body_list = self._create_silence_definitions(
            number_of_definitions=1)
        resp, response_body = self.monasca_client.get_silence_definition(
            response_body_list[0]['id'])

        self.assertEqual(200, resp.status)
        self._verify_element_set(response_body)
        self._verify_silence_definitions_element(response_body,
                                                 response_body_list[0])
        links = response_body['links']
        self._verify_list_silence_definitions_links(links)

    @test.attr(type="python_only")
    def test_get_silence_rule_definitions_with_multibyte_character(self):
        name = data_utils.rand_name('ｄｅｆｉｎｉｔｉｏｎ').decode('utf8')
        description = 'ｄｅｓｃｒｉｐｔｉｏｎ'.decode('utf8')
        response_body_list = self._create_silence_definitions(
            number_of_definitions=1, name=name, description=description)
        resp, response_body = self.monasca_client.get_silence_definition(
            response_body_list[0]['id'])

        self.assertEqual(200, resp.status)
        self._verify_element_set(response_body)
        self._verify_silence_definitions_element(response_body,
                                                 response_body_list[0])
        links = response_body['links']
        self._verify_list_silence_definitions_links(links)

    @test.attr(type="python_only")
    @test.attr(type='negative')
    def test_get_silence_defintion_with_invalid_id(self):
        def_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.get_silence_definition, def_id)

    # Update

    @test.attr(type="python_only")
    def test_update_silence_definition(self):
        matchers = {"severity": "HIGH"}
        response_body_list = self._create_silence_definitions(
            matchers=matchers, number_of_definitions=1)
        # Update silence definition
        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_silence_duration = '5m'
        updated_start_time = "2017-04-10T10:42:10.685Z"

        resp, response_body = self.monasca_client.update_silence_definition(
            str(response_body_list[0]['id']), updated_name, updated_description,
            matchers, updated_start_time, updated_silence_duration)
        self.assertEqual(200, resp.status)
        self._verify_update_patch_silence_definition(response_body, updated_name,
                                                     updated_description, matchers,
                                                     updated_start_time,
                                                     updated_silence_duration)
        # Validate fields updated
        resp, response_body = self.monasca_client.get_silence_definition(
            response_body_list[0]['id'])
        self._verify_update_patch_silence_definition(response_body, updated_name,
                                                     updated_description, matchers,
                                                     updated_start_time,
                                                     updated_silence_duration)
        links = response_body['links']
        self._verify_list_silence_definitions_links(links)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_update_silence_definition_with_different_matchers(self):
        response_body_list = self._create_silence_definitions(
            number_of_definitions=1)
        # Update silence definition
        updated_matchers = {"severity": "HIGH"}
        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_silence_duration = '5m'
        updated_start_time = "2017-04-10T10:42:10.685Z"

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.update_silence_definition,
            str(response_body_list[0]['id']), updated_name, updated_description,
            updated_matchers, updated_start_time, updated_silence_duration)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_update_silence_definition_with_no_matchers(self):
        response_body_list = self._create_silence_definitions(
            number_of_definitions=1)
        # Update silence definition
        updated_matchers = None
        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_silence_duration = '5m'
        updated_start_time = "2017-04-10T10:42:10.685Z"

        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.update_silence_definition,
            str(response_body_list[0]['id']), updated_name, updated_description,
            updated_matchers, updated_start_time, updated_silence_duration)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_update_silence_definition_with_invalid_id(self):
        def_id = data_utils.rand_name()
        self._create_silence_definitions(number_of_definitions=1)
        # Update silence definition
        updated_matchers = {"severity": "HIGH"}
        updated_name = data_utils.rand_name('updated_name')
        updated_description = 'updated description'
        updated_silence_duration = '5m'
        updated_start_time = "2017-04-10T10:42:10.685Z"

        self.assertRaises(
            exceptions.NotFound,
            self.monasca_client.update_silence_definition,
            def_id, updated_name, updated_description,
            updated_matchers, updated_start_time, updated_silence_duration)

    # Patch

    @test.attr(type="python_only")
    def test_patch_silence_rule_definitions(self):
        response_body_list = self._create_silence_definitions(
            number_of_definitions=1)
        # Patch alarm definition
        resp, response_body = self.monasca_client.patch_silence_definition(
            id=response_body_list[0]['id']
        )
        self.assertEqual(200, resp.status)

    @test.attr(type="python_only")
    def test_patch_silence_rule_definitions_with_optional_params(self):
        matchers = {"severity": "HIGH"}
        response_body_list = self._create_silence_definitions(
            number_of_definitions=1, matchers=matchers)
        # Patch alarm definition
        patched_name = data_utils.rand_name('patched_name')
        patched_description = 'updated description'
        patched_start_time = "2017-05-11T10:42:10.685Z"
        patched_silence_duration = '1d2h3m'
        resp, response_body = self.monasca_client.patch_silence_definition(
            id=response_body_list[0]['id'], name=patched_name,
            description=patched_description, start_time=patched_start_time,
            silence_duration=patched_silence_duration
        )
        self.assertEqual(200, resp.status)
        self._verify_update_patch_silence_definition(response_body, patched_name,
                                                     patched_description, matchers,
                                                     patched_start_time,
                                                     patched_silence_duration)
        # validate fields updated
        resp, response_body = self.monasca_client.get_silence_definition(
            response_body_list[0]['id'])
        self._verify_update_patch_silence_definition(response_body, patched_name,
                                                     patched_description, matchers,
                                                     patched_start_time,
                                                     patched_silence_duration)

    @test.attr(type="python_only")
    @test.attr(type="negative")
    def test_patch_silence_rule_definitions_with_different_matchers(self):
        response_body_list = self._create_silence_definitions(
            number_of_definitions=1)
        # Patch alarm definition
        patched_matchers = {"test": "patchedValue"}
        self.assertRaises(
            exceptions.UnprocessableEntity,
            self.monasca_client.patch_silence_definition,
            id=response_body_list[0]['id'], matchers=patched_matchers)

    @test.attr(type="negative")
    @test.attr(type="python_only")
    def test_patch_silence_rule_definitions_with_invalid_id(self):
        def_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.patch_silence_definition,
                          id=def_id, name='Test')

    # Delete

    @test.attr(type="python_only")
    def test_delete_silence_rule_definitions(self):
        response_body_list = self._create_silence_definitions(
            number_of_definitions=1)
        # Delete alarm definitions
        resp, response_body = self.monasca_client.list_silence_definitions()
        self._verify_list_silence_definitions_response_body(resp, response_body)
        elements = response_body['elements']
        for element in elements:
            if element['id'] == response_body_list[0]['id']:
                resp, body = self.monasca_client.delete_silence_definition(
                    response_body_list[0]['id'])
                self.assertEqual(204, resp.status)
                self.assertRaises(exceptions.NotFound,
                                  self.monasca_client.get_silence_definition,
                                  response_body_list[0]['id'])
                return
        self.fail("Failed test_create_and_delete_silence_definition: "
                  "cannot find the alarm definition just created.")

    @test.attr(type="negative")
    @test.attr(type="python_only")
    def test_delete_silence_rule_definitions_with_invalid_id(self):
        def_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.delete_silence_definition, def_id)

    # Helpers

    def _verify_create_silence_definitions(self, resp, response_body,
                                           silence_definition):
        self.assertEqual(201, resp.status)
        self.assertEqual(silence_definition['name'], response_body['name'])

        self.assertEqual(silence_definition['matchers'],
                         response_body['matchers'])

        if 'description' in silence_definition:
            self.assertEqual(silence_definition['description'],
                             str(response_body['description']))
        else:
            self.assertEqual('', str(response_body['description']))
        if 'silence_duration' in silence_definition:
            self.assertEqual(silence_definition['silence_duration'],
                             response_body['silence_duration'])
        else:
            self.assertEqual('10m', response_body['silence_duration'])
        if 'start_time' in silence_definition:
            self.assertEqual(silence_definition['start_time'],
                             str(response_body['start_time']))

    def _create_silence_definitions(self, number_of_definitions, **kwargs):
        matchers = kwargs.get('matchers', {'severity': data_utils.rand_name('LOW')})
        silence_duration = kwargs.get('silence_duration', '5m')
        start_time = kwargs.get('start_time', "2017-04-10T10:42:10.685Z")
        response_body_list = []
        for i in xrange(number_of_definitions):

            name = kwargs.get('name',
                              data_utils.rand_name('silence_definition'))
            desc = kwargs.get('description',
                              data_utils.rand_name('description'))

            silence_definition = helpers.create_silence_definition(
                name=name,
                description=desc,
                matchers=matchers,
                silence_duration=silence_duration,
                start_time=start_time
            )
            resp, response_body = self.monasca_client.create_silence_definitions(
                silence_definition)
            self.assertEqual(201, resp.status)
            response_body_list.append(response_body)
        return response_body_list

    def _verify_list_silence_definitions_response_body(self, resp, response_body):
        self.assertEqual(200, resp.status)
        self.assertIsInstance(response_body, dict)
        self.assertTrue(set(['links', 'elements']) == set(response_body))

    def _verify_silence_definitions_list(self, observed, reference):
        self.assertEqual(len(reference), len(observed))
        for i in xrange(len(reference)):
            self._verify_silence_definitions_element(
                reference[i], observed[i])

    def _verify_silence_definitions_element(self, response_body, res_body_create_silence):
        self._verify_element_set(response_body)
        self.assertEqual(response_body['name'],
                         res_body_create_silence['name'])
        self.assertEqual(response_body['description'],
                         res_body_create_silence['description'])
        self.assertEqual(response_body['matchers'],
                         res_body_create_silence['matchers'])
        self.assertEqual(response_body['start_time'],
                         res_body_create_silence['start_time'])
        self.assertEqual(response_body['silence_duration'],
                         res_body_create_silence['silence_duration'])

    def _verify_element_set(self, element):
        self.assertTrue(set(['id',
                             'links',
                             'name',
                             'description',
                             'matchers',
                             'start_time',
                             'silence_duration']) ==
                        set(element))

    def _verify_list_silence_definitions_links(self, links):
        self.assertIsInstance(links, list)
        link = links[0]
        self.assertTrue(set(['rel', 'href']) == set(link))
        self.assertEqual(link['rel'], u'self')

    def _verify_update_patch_silence_definition(self, response_body,
                                                updated_name, updated_description,
                                                updated_matchers, updated_start_time,
                                                updated_silence_duration):
        if updated_name is not None:
            self.assertEqual(updated_name, response_body['name'])
        if updated_description is not None:
            self.assertEqual(updated_description, response_body['description'])
        if updated_matchers is not None:
            self.assertEqual(updated_matchers, response_body['matchers'])
        if updated_start_time is not None:
            self.assertEqual(updated_start_time, response_body['start_time'])
        if updated_silence_duration is not None:
            self.assertEqual(updated_silence_duration, response_body['silence_duration'])
