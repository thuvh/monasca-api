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

from tempest.lib.common.utils import data_utils
from tempest import test

from monasca_tempest_tests.tests.api import base
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
