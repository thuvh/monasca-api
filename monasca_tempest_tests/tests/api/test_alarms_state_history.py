# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

# TODO(RMH): Update documentation. Get alarms returns alarm_definition, not
# TODO(RMH): alarm_definition_id in response body
import time

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import helpers
from oslo_utils import timeutils
from tempest.common.utils import data_utils
from tempest import test

NUM_ALARM_DEFINITIONS = 3


class TestAlarmsStateHistory(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestAlarmsStateHistory, cls).resource_setup()

        cls._test_start_time = timeutils.iso8601_from_timestamp(
            int(time.time()) - 60)

        for i in xrange(1, NUM_ALARM_DEFINITIONS + 1):
            alarm_definition = helpers.create_alarm_definition(
                name=data_utils.rand_name('alarm_definition' + str(i)),
                expression="min(name-1) < " + str(i))
            cls.monasca_client.create_alarm_definitions(alarm_definition)

        # create some metrics to prime the system and create three alarms
        for i in xrange(60):
            metric = helpers.create_metric()
            cls.monasca_client.create_metrics(metric)
            resp, response_body = cls.monasca_client.\
                list_alarms_state_history()
            elements = response_body['elements']
            if len(elements) >= NUM_ALARM_DEFINITIONS:
                break
            time.sleep(5)

    @test.attr(type="gate")
    def test_list_alarms_state_history(self):
        resp, response_body = self.monasca_client.list_alarms_state_history()
        self.assertEqual(200, resp.status)
        # Test response body
        self.assertTrue(set(['links', 'elements']) == set(response_body))
        elements = response_body['elements']
        number_of_alarms = len(elements)
        if number_of_alarms < 1:
            error_msg = "Failed test_list_alarms_state_history: need " \
                        "at least one alarms state history to test."
            self.fail(error_msg)
        else:
            element = elements[0]
            self.assertTrue(set(['id', 'alarm_id', 'metrics', 'old_state',
                                 'new_state', 'reason', 'reason_data',
                                 'timestamp', 'sub_alarms'])
                            == set(element))

    @test.attr(type="gate")
    def test_list_alarms_state_history_with_dimensions(self):
        resp, response_body = self.monasca_client.list_alarms_state_history()
        elements = response_body['elements']
        if elements:
            element = elements[0]
            dimension = element['metrics'][0]['dimensions']
            dimension_items = dimension.items()
            dimension_item = dimension_items[0]
            dimension_item_0 = dimension_item[0]
            dimension_item_1 = dimension_item[1]
            name = element['metrics'][0]['name']

            query_parms = '?dimensions=' + str(dimension_item_0) + ':' + str(
                dimension_item_1)
            resp, response_body = self.monasca_client.\
                list_alarms_state_history(query_parms)
            name_new = response_body['elements'][0]['metrics'][0]['name']
            self.assertEqual(200, resp.status)
            self.assertEqual(name, name_new)
        else:
            error_msg = "Failed test_list_alarms_state_history_with_" \
                        "dimensions: need at least one alarms state history " \
                        "to test."
            self.fail(error_msg)

    @test.attr(type="gate")
    def test_list_alarms_state_history_with_start_time(self):
        current_timestamp = int(time.time())
        current_time = timeutils.iso8601_from_timestamp(current_timestamp)
        end_time = timeutils.iso8601_from_timestamp(current_timestamp + 120)
        query_parms = '?start_time=' + str(current_time) + '&end_time=' + \
                      str(end_time)
        resp, response_body = self.monasca_client.list_alarms_state_history(
            query_parms)
        elements = response_body['elements']
        self.assertEqual(0, len(elements))
        return
        resp, response_body = self.monasca_client.list_alarms_state_history()
        elements = response_body['elements']
        timestamp = elements[1]['timestamp']
        query_parms = '?start_time=' + str(timestamp)
        resp, response_body = self.monasca_client.list_alarms_state_history(
            query_parms)
        elements = response_body['elements']
        self.assertEqual(2, len(elements))

    @test.attr(type="gate")
    def test_list_alarms_state_history_with_end_time(self):
        query_parms = '?end_time=' + str(self._test_start_time)
        resp, response_body = self.monasca_client.list_alarms_state_history(
            query_parms)
        elements = response_body['elements']
        self.assertEqual(0, len(elements))
        return
        resp, response_body = self.monasca_client.list_alarms_state_history()
        elements = response_body['elements']
        timestamp = elements[2]['timestamp']
        query_parms = '?end_time=' + str(timestamp)
        resp, response_body = self.monasca_client.list_alarms_state_history(
            query_parms)
        elements = response_body['elements']
        self.assertEqual(1, len(elements))

    @test.attr(type="gate")
    def test_list_alarms_state_history_with_offset_limit(self):
        resp, response_body = self.monasca_client.list_alarms_state_history()
        elements = response_body['elements']
        number_of_alarms = len(elements)
        if number_of_alarms >= NUM_ALARM_DEFINITIONS:
            orig_elements = elements[:]
            first_element = orig_elements[0]
            second_element = orig_elements[1]
            first_element_id = first_element['id']
            second_element_id = second_element['id']

            for limit in xrange(1, NUM_ALARM_DEFINITIONS + 1):
                query_parms = '?limit=' + str(limit) + \
                              '&offset=' + str(first_element_id)
                resp, response_body = self.monasca_client.\
                    list_alarms_state_history(query_parms)
                elements = response_body['elements']
                element_new = elements[0]
                self.assertEqual(200, resp.status)

                # first_element is actually member of "previous" page
                self.assertNotEqual(element_new, first_element)
                self.assertEqual(element_new, second_element)
                # limit as always > because first elements is excluded
                # due to offset condition in API
                self.assertTrue(limit >= len(elements))
                if len(elements) > 0:
                    # check only limit allowed some elements to be returned
                    id_new = element_new['id']
                    self.assertNotEqual(id_new, first_element_id)
                    self.assertEqual(id_new, second_element_id)
        else:
                error_msg = ("Failed "
                             "test_list_alarms_state_history_with_offset "
                             "limit: need three alarms state history to "
                             "test. Current number of alarms = {}").\
                    format(number_of_alarms)
                self.fail(error_msg)

    @test.attr(type="gate")
    def test_list_alarm_state_history(self):
        # Get the alarm state history for a specific alarm by ID
        resp, response_body = self.monasca_client.list_alarms_state_history()
        self.assertEqual(200, resp.status)
        elements = response_body['elements']
        if elements:
            element = elements[0]
            alarm_id = element['alarm_id']
            resp, response_body = self.monasca_client.list_alarm_state_history(
                alarm_id)
            self.assertEqual(200, resp.status)

            # Test Response Body
            self.assertTrue(set(['links', 'elements']) ==
                            set(response_body))
            elements = response_body['elements']
            links = response_body['links']
            self.assertTrue(isinstance(links, list))
            link = links[0]
            self.assertTrue(set(['rel', 'href']) ==
                            set(link))
            self.assertEqual(link['rel'], u'self')
            definition = elements[0]
            self.assertTrue(set(['id', 'alarm_id', 'metrics', 'new_state',
                                 'old_state', 'reason', 'reason_data',
                                 'sub_alarms', 'timestamp']) ==
                            set(definition))
        else:
            error_msg = "Failed test_list_alarm_state_history: at least one " \
                        "alarm state history is needed."
            self.fail(error_msg)

    @test.attr(type="gate")
    def test_list_alarm_state_history_with_offset_limit(self):
        # Get the alarm state history for a specific alarm by ID
        resp, response_body = self.monasca_client.list_alarms_state_history()
        self.assertEqual(200, resp.status)
        elements = response_body['elements']
        if elements:
            element = elements[0]
            alarm_id = element['alarm_id']
            query_params = '?limit=1'
            resp, response_body = (self.monasca_client
                                   .list_alarm_state_history(alarm_id,
                                                             query_params))
            elements = response_body['elements']
            self.assertEqual(200, resp.status)
            self.assertEqual(1, len(elements))
            self.assertEqual(element, elements[0])

            element_id = element['id']
            query_params = '?limit=1&offset=' + str(element_id)
            resp, response_body = (self.monasca_client
                                   .list_alarm_state_history(alarm_id,
                                                             query_params))
            elements_new = response_body['elements']
            self.assertEqual(200, resp.status)
            self.assertEqual(0, len(elements_new))
        else:
            error_msg = "Failed test_list_alarm_state_history_with_offset" \
                        "_limit: at least one alarms state history is needed."
            self.fail(error_msg)

    @test.attr(type="gate")
    def test_alarm_state_history_paging(self):
        resp, response_body = self.monasca_client.list_alarms_state_history()
        self.assertEqual(200, resp.status)
        elements = response_body['elements']
        if elements:
            first_element = elements[0]
            first_element_id = first_element['id']
            len_of_elements = len(elements)
            limit = len_of_elements + 1

            # verify if the same result with limit as without
            params = '?limit=%s' % str(limit)
            resp, response_body = (self.monasca_client
                                   .list_alarms_state_history(params))
            elements = response_body['elements']
            self.assertEqual(200, resp.status)
            self.assertEqual(len_of_elements, len(elements))

            # verify paging for all ids with next limits
            el_ids = [tmp['id'] for tmp in elements]  # collects ids for paging
            for el_id in el_ids:
                for limit in xrange(1, len_of_elements + 1):
                    # test goes through each el_id with each limit to check
                    # if paging works correctly

                    params = '?limit=%s&offset=%s' % (str(limit), str(el_id))
                    resp, response_body = (self.monasca_client
                                           .list_alarms_state_history(params))
                    elements = response_body['elements']
                    self.assertEqual(200, resp.status)

                    # only check if element is not penultimate
                    if el_ids.index(el_id) != len(el_ids) - 1:
                        # should have elements, less than limit
                        self.assertTrue(limit >= len(elements))

                        first_element = elements[0]
                        first_element_id = first_element['id']
                        e_first_element_id = el_ids[el_ids.index(el_id) + 1]
                        # element in limit should be missing
                        # i.e. it is the last element on previous page
                        self.assertNotEqual(el_id, first_element['id'])
                        self.assertEqual(e_first_element_id,
                                         first_element_id)
                    else:
                        # should be empty page for last el_id
                        self.assertTrue(len(elements) == 0)

        else:
            error_msg = "Failed test_alarm_state_history_paging" \
                        ", at least one alarms state history is needed."
            self.fail(error_msg)
