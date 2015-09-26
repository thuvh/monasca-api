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

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import helpers
from tempest.common.utils import data_utils
from tempest import test


class TestAlarmsStateHistory(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        # create an alarm definition
        expression = "avg(name-1) > 0"
        name = data_utils.rand_name('name-1')
        resp, _ = cls.monasca_client.create_alarm_definition(
            name=name,
            expression=expression)

        # create some metrics
        for i in xrange(100):
            metric = helpers.create_metric()
            resp, body = cls.monasca_client.create_metrics(metric)

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
    def test_list_alarms_state_history_with_dimensions(self):
        return

    @test.attr(type="gate")
    def test_list_alarms_state_history_with_start_time(self):
        return

    @test.attr(type="gate")
    def test_list_alarms_state_history_with_end_time(self):
        return

    @test.attr(type="gate")
    def test_list_alarms_state_history_with_offset_limit(self):
        return

    @test.attr(type="gate")
    def test_get_alarm_state_history(self):
        # Get the alarm state history for a specific alarm by ID
        return

    @test.attr(type="gate")
    def test_get_alarm_state_history_with_invalid_id(self):
        return
