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
import sys
import time

from oslo_utils import timeutils

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import helpers
from tempest.common.utils import data_utils
from tempest import test


class TestAlarmsStateHistory(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestAlarmsStateHistory, cls).resource_setup()

        start_timestamp = int(time.time() * 1000)
        end_timestamp = int(time.time() * 1000) + 1000

        # create an alarm definition
        expression = "avg(name-1) > 0"
        name = data_utils.rand_name('name-1')
        alarm_definition = helpers.create_alarm_definition(
            name=name,
            expression=expression)
        resp, response_body = cls.monasca_client.create_alarm_definitions(
            alarm_definition)

        # create some metrics
        for i in xrange(180):
            metric = helpers.create_metric()
            resp, body = cls.monasca_client.create_metrics(metric)
            cls._start_timestamp = start_timestamp + i
            cls._end_timestamp = end_timestamp + i
            time.sleep(1)
            resp, response_body = cls.monasca_client.\
                list_alarms_state_history()
            elements = response_body['elements']
            if len(elements) > 0:
                break

        if len(elements) < 1:
            sys.exit()

    @classmethod
    def resource_cleanup(cls):
        super(TestAlarmsStateHistory, cls).resource_cleanup()
        resp, response_body = cls.monasca_client.list_alarm_definitions()
        elements = response_body['elements']
        for element in elements:
            id = element['id']
            resp, response_body = \
                cls.monasca_client.delete_alarm_definition(id)

    @test.attr(type="gate")
    def test_list_alarms_state_history(self):
        resp, response_body = self.monasca_client.list_alarms_state_history()
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_alarm_state_history_with_offset_limit(self):
        query_parms = '?offset=1&limit=2'
        # Get the alarm state history for a specific alarm by ID
        resp, response_body = self.monasca_client.list_alarms_state_history()
        self.assertEqual(200, resp.status)
        elements = response_body['elements']
        element = elements[0]
        alarm_id = element['alarm_id']
        resp, response_body = self.monasca_client.list_alarm_state_history(
            alarm_id, query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_alarms_state_history_with_dimensions(self):
        query_parms = '?dimensions=key1:value1'
        resp, response_body = self.monasca_client.list_alarms_state_history(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_alarms_state_history_with_start_time(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?start_time' + str(start_time)
        resp, response_body = self.monasca_client.list_alarms_state_history(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_alarms_state_history_with_end_time(self):
        end_time = timeutils.iso8601_from_timestamp(
            self._end_timestamp / 1000)
        query_parms = '?end_time' + str(end_time)
        resp, response_body = self.monasca_client.list_alarms_state_history(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_alarms_state_history_with_offset_limit(self):
        query_parms = '?offset=1&limit=2'
        resp, response_body = self.monasca_client.list_alarms_state_history(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_alarm_state_history(self):
        # Get the alarm state history for a specific alarm by ID
        resp, response_body = self.monasca_client.list_alarms_state_history()
        self.assertEqual(200, resp.status)
        elements = response_body['elements']
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
