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
from tempest.lib import decorators

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import constants
from monasca_tempest_tests.tests.api import helpers


NUM_GROUP_DEFINITIONS = 2


class TestAlarmInhibitionDefinitions(base.BaseMonascaTest):

    # Create

    @decorators.attr(type="python_only")
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

    @decorators.attr(type="python_only")
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

    @decorators.attr(type="python_only")
    @decorators.attr(type="negative")
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

    @decorators.attr(type="python_only")
    def test_list_inhibition_rule_definitions(self):
        source_match = {'severity': 'HIGH'}
        target_match = {'severity': 'LOW'}
        equal = ['name']
        response_body_list = self._create_inhibition_definitions(
            source_match=match, target_match=target_match, equal=equal,
            number_of_definitions=1)
        query_param = '?name=' + str(response_body_list[0]['name'])
        resp, response_body = self.monasca_client.list_inhibition_definitions(
            query_param)

        # Test list alarm inhibition definition response body
        self._verify_list_inhibition_definitions_response_body(resp, response_body)

        elements = response_body['elements']
        self._verify_inhibition_definitions_list(elements, response_body_list)

        links = response_body['links']
        self._verify_list_inhibition_definitions_links(links)

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
        equal = kwargs.get('equal', {'alarmName', 'alarm1'})
        exclusions = kwargs.get('exclusions', {})
        response_body_list = []
        for i in xrange(number_of_definitions):

            name = kwargs.get('name',
                              data_utils.rand_name('alarm_definition'))
            desc = kwargs.get('description',
                              data_utils.rand_name('description'))

            alarm_definition = helpers.create_inhibition_definition(
                name = name,
                descpription = description,
                source_match=source_match,
                target_match=target_match,
                equal=equal,
                exclusions=exclusions
            )
            resp, response_body = self.monasca_client.create_inhibition_definitions(
                alarm_definition)
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
            self._verify_group_definitions_element(
                reference[i], observed[i])

    def _verify_list_inhibition_definitions_links(self, links):
        self.assertIsInstance(links, list)
        link = links[0]
        self.assertTrue(set(['rel', 'href']) == set(link))
        self.assertEqual(link['rel'], u'self')
