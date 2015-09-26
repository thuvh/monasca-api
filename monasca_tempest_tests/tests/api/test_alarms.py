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
from tempest_lib import exceptions


class TestAlarms(base.BaseMonascaTest):

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
        super(TestAlarms, cls).resource_cleanup()
        resp, response_body = cls.monasca_client.list_alarm_definitions()
        elements = response_body['elements']
        for element in elements:
            id = element['id']
            resp, response_body = \
                cls.monasca_client.delete_alarm_definition(
                    id)

    @test.attr(type="gate")
    def test_list_alarms(self):
        resp, response_body = self.monasca_client.list_alarms()
        self.assertEqual(200, resp.status)
        self.assertTrue(set(['links', 'elements']) ==
                        set(response_body))
        elements = response_body['elements']
        alarm = elements[0]

        self.assertTrue(set(['id',
                             'links',
                             'alarm_definition',
                             'metrics',
                             'state',
                             'lifecycle_state',
                             'link',
                             'state_updated_timestamp',
                             'updated_timestamp',
                             'created_timestamp']) ==
                        set(alarm))

        for metric in alarm['metrics']:
            target_metric = helpers.create_metric()
            self.assertEqual(target_metric['name'], metric['name'])
            self.assertEqual(target_metric['dimensions'], metric['dimensions'])

    @test.attr(type="gate")
    def test_list_alarms_by_alarm_definition_id(self):
        return

    @test.attr(type="gate")
    def test_list_alarms_by_metric_name(self):
        return

    @test.attr(type="gate")
    def test_list_alarms_by_metric_dimensions(self):
        return

    @test.attr(type="gate")
    def test_list_alarms_by_state(self):
        return

    @test.attr(type="gate")
    def test_list_alarms_by_lifecycle_state(self):
        return

    @test.attr(type="gate")
    def test_list_alarms_by_link(self):
        return

    @test.attr(type="gate")
    def test_list_alarms_by_state_updated_start_time(self):
        return

    @test.attr(type="gate")
    def test_get_alarm(self):
        resp, response_body = self.monasca_client.list_alarms()
        self.assertEqual(200, resp.status)
        elements = response_body['elements']
        alarm = elements[0]
        id = alarm['id']
        resp, response_body = self.monasca_client.get_alarm(id)
        self.assertEqual(200, resp.status)
        self.assertTrue(set(['id',
                             'links',
                             'alarm_definition',
                             'metrics',
                             'state',
                             'lifecycle_state',
                             'link',
                             'state_updated_timestamp',
                             'updated_timestamp',
                             'created_timestamp']) ==
                        set(response_body))
        for metric in alarm['metrics']:
            target_metric = helpers.create_metric()
            self.assertEqual(target_metric['name'], metric['name'])
            self.assertEqual(target_metric['dimensions'], metric['dimensions'])

    @test.attr(type="gate")
    def test_get_alarm_invalid_id(self):
        id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.get_alarm,
                          id)

    @test.attr(type="gate")
    def test_delete_alarm(self):
        return

    @test.attr(type="gate")
    def test_delete_alarm_invalid_id(self):
        return

    @test.attr(type="gate")
    def test_update_alarm(self):
        return
