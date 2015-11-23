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
from monasca_tempest_tests.tests.api import constants
from monasca_tempest_tests.tests.api import helpers
from tempest.common.utils import data_utils
from tempest import test
from tempest_lib import exceptions


class TestAlarms(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestAlarms, cls).resource_setup()

        # set up alarm definitions and alarms
        cls.alarm_definition_ids = []
        cls.all_alarms = []

        metric_name_1 = data_utils.rand_name('name_1')
        # some tests need access to this
        cls.metric_name_1 = metric_name_1
        key_1 = data_utils.rand_name('key_1')

        # create first alarm definition
        expression_1 = "avg(" + metric_name_1 + ") > 0"
        name_1 = data_utils.rand_name('name_1')
        alarm_definition = helpers.create_alarm_definition(
            name=name_1, expression=expression_1, match_by=[key_1])
        resp, response_body = cls.monasca_client.create_alarm_definitions(
            alarm_definition)
        cls.alarm_definition_ids.append(response_body['id'])

        # create some metrics for 3 alarms
        for j in xrange(3):
            value = data_utils.rand_name("value")
            expected_metric_1 = helpers.create_metric(name=metric_name_1,
                                                      dimensions={key_1: value})
            cls.monasca_client.create_metrics(expected_metric_1)
            for i in xrange(constants.MAX_RETRIES):
                time.sleep(constants.RETRY_WAIT_SECS)
                query_param = '?alarm_definition_id=' + \
                              str(cls.alarm_definition_ids[-1])
                resp, response_body = cls.monasca_client.list_alarms(
                    query_param)
                elements = response_body['elements']
                if len(elements) >= j:
                    break

        # create second alarm definition
        metric_name_2 = data_utils.rand_name('name_2')
        key_2 = data_utils.rand_name('key_2')
        expression_2 = "max(" + metric_name_2 + ") > 0"
        name_2 = data_utils.rand_name('name_2')
        alarm_definition = helpers.create_alarm_definition(
            name=name_2, expression=expression_2, match_by=[key_2])
        resp, response_body = cls.monasca_client.create_alarm_definitions(
            alarm_definition)
        cls.alarm_definition_ids.append(response_body['id'])

        # create metric for one alarm definition
        value = data_utils.rand_name("value")
        expected_metric_2 = helpers.create_metric(name=metric_name_2,
                                                  dimensions={key_1: value})
        cls.monasca_client.create_metrics(expected_metric_2)
        for i in xrange(constants.MAX_RETRIES):
            time.sleep(constants.RETRY_WAIT_SECS)
            query_param = '?alarm_definition_id=' + \
                          str(cls.alarm_definition_ids[-1])
            resp, response_body = cls.monasca_client.list_alarms(
                query_param)
            elements = response_body['elements']
            if len(elements) >= 1:
                break

        resp, response_body = cls.monasca_client.list_alarms()
        assert resp.status == 200, "Failed to list alarms"
        cls.all_alarms = response_body['elements']

        target_id = cls.all_alarms[0]['id']
        resp, response_body = cls.monasca_client.patch_alarm(target_id,
                                                             lifecycle_state="OPEN")
        assert resp.status == 200, "Unable to patch alarm lifecycle_state during setup"

        resp, response_body = cls.monasca_client.get_alarm(target_id)
        cls.all_alarms[0] = response_body

        target_id_2 = cls.all_alarms[1]['id']
        resp, response_body = cls.monasca_client.patch_alarm(target_id_2,
                                                             link="http://somesite.com/this-alarm-info")
        assert resp.status == 200, "Unable to patch alarm link during setup"

        resp, response_body = cls.monasca_client.get_alarm(target_id_2)
        cls.all_alarms[1] = response_body

        # make sure tests are running after the current alarm timestamps
        time.sleep(2)

    @classmethod
    def resource_cleanup(cls):
        super(TestAlarms, cls).resource_cleanup()
        for definition_id in cls.alarm_definition_ids:
            try:
                cls.monasca_client.delete_alarm_definition(definition_id)
            except exceptions.NotFound:
                pass

    @test.attr(type="gate")
    def test_list_alarms(self):
        resp, response_body = self.monasca_client.list_alarms()
        self.assertEqual(200, resp.status)
        elements = response_body['elements']

        for i in xrange(len(self.all_alarms)):
            self._verify_alarm_keys(elements[i])
            self.assertTrue(self.all_alarms[i] in elements)

    @test.attr(type="gate")
    def test_list_alarms_by_alarm_definition_id(self):
        definition_id = self.alarm_definition_ids[0]
        expected_alarms = [alarm for alarm in self.all_alarms
                           if alarm['alarm_definition']['id'] == definition_id]

        query_param = '?alarm_definition_id=' + definition_id
        resp, response_body = self.monasca_client.list_alarms(query_param)
        self._verify_list_alarms_elements(resp, response_body,
                                          expect_num_elements=3)
        elements = response_body['elements']
        for i in xrange(len(elements)):
            self.assertEqual(expected_alarms[i], elements[i])

    @test.attr(type="gate")
    def test_list_alarms_by_metric_name(self):
        metric_name = self.metric_name_1
        expected_alarms = [alarm for alarm in self.all_alarms
                           if metric_name == alarm['metrics'][0]['name']]

        query_parms = '?metric_name=' + self.metric_name_1
        resp, response_body = self.monasca_client.list_alarms(query_parms)
        self._verify_list_alarms_elements(resp, response_body,
                                          expect_num_elements=3)
        elements = response_body['elements']
        for i in xrange(len(elements)):
            self.assertEqual(expected_alarms[i], elements[i])


    @test.attr(type="gate")
    def test_list_alarms_by_metric_dimensions(self):
        expected_metric = self.all_alarms[0]['metrics'][0]
        dimensions = []
        for key in expected_metric['dimensions']:
            value = expected_metric['dimensions'][key]
            dimensions.append(key + ":" + value)
        query_parms = '?metric_dimensions=' + ",".join(dimensions)
        resp, response_body = self.monasca_client.list_alarms(query_parms)
        self._verify_list_alarms_elements(resp, response_body,
                                          expect_num_elements=1)
        element = response_body['elements'][0]
        self.assertEqual(element, self.all_alarms[0])



    @test.attr(type="gate")
    def test_list_alarms_by_state(self):
        resp, response_body = self.monasca_client.list_alarms()
        self._verify_list_alarms_elements(resp, response_body)
        elements = response_body['elements']
        num_total = len(elements)

        query_parms = '?state=UNDETERMINED'
        resp, response_body1 = self.monasca_client.list_alarms(query_parms)
        self.assertEqual(200, resp.status)
        num_undetermined = len(response_body1['elements'])

        query_parms = '?state=OK'
        resp, response_body2 = self.monasca_client.list_alarms(query_parms)
        self.assertEqual(200, resp.status)
        num_ok = len(response_body2['elements'])

        query_parms = '?state=ALARM'
        resp, response_body3 = self.monasca_client.list_alarms(query_parms)
        self.assertEqual(200, resp.status)
        num_alarm = len(response_body3['elements'])

        self.assertEqual(num_total, num_undetermined + num_ok + num_alarm)

    @test.attr(type="gate")
    def test_list_alarms_by_lifecycle_state(self):
        query_parms = '?lifecycle_state=OPEN'
        resp, response_body = self.monasca_client.list_alarms(query_parms)
        self._verify_list_alarms_elements(resp, response_body,
                                          expect_num_elements=1)
        element = response_body['elements'][0]
        self.assertEqual(element, self.all_alarms[0])


    @test.attr(type="gate")
    def test_list_alarms_by_link(self):
        query_parms = '?link=http://somesite.com/this-alarm-info'
        resp, response_body = self.monasca_client.list_alarms(query_parms)
        self._verify_list_alarms_elements(resp, response_body,
                                          expect_num_elements=1)
        element = response_body['elements'][0]
        self.assertEqual(element, self.all_alarms[1])

    @test.attr(type="gate")
    def test_list_alarms_by_state_updated_start_time(self):
        state_updated_start_time = self.all_alarms[2]['state_updated_timestamp']
        expected_alarms = [alarm for alarm in self.all_alarms
                           if alarm['state_updated_timestamp'] >= state_updated_start_time]

        query_parms = '?state_updated_timestamp=' + str(state_updated_start_time)
        resp, response_body = self.monasca_client.list_alarms(query_parms)
        self._verify_list_alarms_elements(resp, response_body)
        elements = response_body['elements']

        for alarm in elements:
            self.assertTrue(alarm['state_updated_timestamp'] >= state_updated_start_time)

    @test.attr(type="gate")
    def test_list_alarms_by_offset_limit(self):
        resp, response_body = self.monasca_client.list_alarms()
        self._verify_list_alarms_elements(resp, response_body)
        elements = response_body['elements']
        first_element = elements[0]
        next_element = elements[1]
        id_first_element = first_element['id']
        query_parms = '?offset=' + str(id_first_element) + '&limit=1'
        resp, response_body1 = self.monasca_client.list_alarms(query_parms)
        elements = response_body1['elements']
        self.assertEqual(1, len(elements))
        self.assertEqual(elements[0]['id'], next_element['id'])
        self.assertEqual(elements[0], next_element)

    @test.attr(type="gate")
    def test_get_alarm(self):
        original_alarm = self.all_alarms[0]
        resp, response_body = self.monasca_client.get_alarm(original_alarm['id'])
        self.assertEqual(200, resp.status)
        self.assertEqual(original_alarm, response_body)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_get_alarm_with_invalid_id(self):
        alarm_id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound, self.monasca_client.get_alarm,
                          alarm_id)

    @test.attr(type="gate")
    def test_update_alarm(self):
        alarms = self._create_alarms_for_test_alarms(num=1)
        original_alarm = alarms[0]

        updated_state = "ALARM"
        updated_lifecycle_state = "ACKNOWLEDGED"
        updated_link = "http://somesite.com"
        resp, response_body = self.monasca_client.update_alarm(
            id=original_alarm['id'], state=updated_state,
            lifecycle_state=updated_lifecycle_state, link=updated_link)
        self.assertEqual(200, resp.status)
        self._verify_alarm_keys(response_body)

        # Validate fields updated
        resp, response_body = self.monasca_client.get_alarm(original_alarm['id'])
        self.assertEqual(updated_state, response_body['state'])
        self.assertEqual(updated_lifecycle_state, response_body['lifecycle_state'])
        self.assertEqual(updated_link, response_body['link'])
        # Validate timestamps
        self.assertNotEqual(original_alarm['state_updated_timestamp'],
                            response_body['state_updated_timestamp'])
        self.assertNotEqual(original_alarm['updated_timestamp'],
                            response_body['updated_timestamp'])

        self.monasca_client.delete_alarm_definition(original_alarm['alarm_definition']['id'])

    @test.attr(type="gate")
    def test_patch_alarm(self):
        alarms = self._create_alarms_for_test_alarms(num=1)
        original_alarm = alarms[0]

        patch_link = "http://somesite.com/all-the-info"
        resp, response_body = self.monasca_client.patch_alarm(
            id=original_alarm['id'], link=patch_link)
        self.assertEqual(200, resp.status)
        self._verify_alarm_keys(response_body)

        # Validate the field patched
        resp, response_body = self.monasca_client.get_alarm(original_alarm['id'])
        self.assertEqual(patch_link, response_body['link'])
        # Validate timestamps
        self.assertEqual(original_alarm['state_updated_timestamp'],
                         response_body['state_updated_timestamp'])
        self.assertNotEqual(original_alarm['updated_timestamp'],
                            response_body['updated_timestamp'])

        self.monasca_client.delete_alarm_definition(original_alarm['alarm_definition']['id'])

    @test.attr(type="gate")
    def test_delete_alarm(self):
        alarms = self._create_alarms_for_test_alarms(num=1)
        alarm_id = alarms[0]['id']

        resp, response_body = self.monasca_client.delete_alarm(alarm_id)
        self.assertEqual(204, resp.status)

        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.get_alarm, alarm_id)

        self.monasca_client.delete_alarm_definition(alarms[0]['alarm_definition']['id'])

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_delete_alarm_with_invalid_id(self):
        id = data_utils.rand_name()
        self.assertRaises(exceptions.NotFound,
                          self.monasca_client.delete_alarm, id)

    @test.attr(type="gate")
    def test_create_alarms_with_match_by(self):
        # Create an alarm definition with no match_by
        name = data_utils.rand_name('alarm_definition_1')
        expression = "avg(cpu.idle_perc{service=monitoring}) < 20"
        alarm_definition = helpers.create_alarm_definition(
            name=name, description="description", expression=expression)
        resp, response_body = self.monasca_client.create_alarm_definitions(
            alarm_definition)
        alarm_definition_id = response_body['id']
        self._create_metrics_for_match_by(
            num=1, alarm_definition_id=alarm_definition_id)
        query_param = '?alarm_definition_id=' + str(alarm_definition_id)
        resp, response_body = self.monasca_client.list_alarms(query_param)
        self._verify_list_alarms_elements(resp, response_body,
                                          expect_num_elements=1)
        elements = response_body['elements']
        metrics = elements[0]['metrics']
        self.assertEqual(len(metrics), 2)
        self.assertNotEqual(metrics[0], metrics[1])

        self.monasca_client.delete_alarm_definition(alarm_definition_id)

        # Create an alarm definition with match_by
        name = data_utils.rand_name('alarm_definition_2')
        expression = "avg(cpu.idle_perc{service=monitoring}) < 20"
        match_by = ['hostname']
        alarm_definition = helpers.create_alarm_definition(
            name=name, description="description", expression=expression,
            match_by=match_by)
        resp, response_body = self.monasca_client.create_alarm_definitions(
            alarm_definition)
        alarm_definition_id = response_body['id']
        # create some metrics
        self._create_metrics_for_match_by(
            num=2, alarm_definition_id=alarm_definition_id)
        query_param = '?alarm_definition_id=' + str(alarm_definition_id)
        resp, response_body = self.monasca_client.list_alarms(query_param)
        self._verify_list_alarms_elements(resp, response_body,
                                          expect_num_elements=2)
        elements = response_body['elements']
        self.assertEqual(len(elements[0]['metrics']), 1)
        self.assertEqual(len(elements[1]['metrics']), 1)
        self.assertNotEqual(elements[0]['metrics'], elements[1]['metrics'])

        self.monasca_client.delete_alarm_definition(alarm_definition_id)

    @test.attr(type="gate")
    def test_create_alarms_with_sub_expressions_and_match_by(self):
        # Create an alarm definition with sub-expressions and match_by
        name = data_utils.rand_name('alarm_definition_3')
        expression = "avg(cpu.idle_perc{service=monitoring}) < 10 or " \
                     "avg(cpu.user_perc{service=monitoring}) > 60"
        match_by = ['hostname']
        alarm_definition = helpers.create_alarm_definition(
            name=name, description="description", expression=expression,
            match_by=match_by)
        resp, response_body = self.monasca_client.create_alarm_definitions(
            alarm_definition)
        alarm_definition_id = response_body['id']
        self._create_metrics_for_match_by_sub_expressions(
            num=2, alarm_definition_id=alarm_definition_id)
        query_param = '?alarm_definition_id=' + str(alarm_definition_id)
        resp, response_body = self.monasca_client.list_alarms(query_param)
        self._verify_list_alarms_elements(resp, response_body,
                                          expect_num_elements=2)
        elements = response_body['elements']
        hostnames = []
        for i in xrange(2):
            self.assertEqual(len(elements[i]['metrics']), 2)
        for i in xrange(2):
            for j in xrange(2):
                hostnames.append(elements[i]['metrics'][j]['dimensions'][
                    'hostname'])
        self.assertEqual(hostnames[0], hostnames[1])
        self.assertEqual(hostnames[2], hostnames[3])
        self.assertNotEqual(hostnames[0], hostnames[2])

        self.monasca_client.delete_alarm_definition(alarm_definition_id)

    @test.attr(type="gate")
    def test_create_alarms_with_match_by_list(self):
        # Create an alarm definition with match_by as a list
        name = data_utils.rand_name('alarm_definition')
        expression = "avg(cpu.idle_perc{service=monitoring}) < 10"
        match_by = ['hostname', 'device']
        alarm_definition = helpers.create_alarm_definition(
            name=name, description="description", expression=expression,
            match_by=match_by)
        resp, response_body = self.monasca_client.create_alarm_definitions(
            alarm_definition)
        alarm_definition_id = response_body['id']
        query_param = '?alarm_definition_id=' + str(alarm_definition_id)
        # create some metrics
        self._create_metrics_for_match_by_sub_expressions_list(
            num=4, alarm_definition_id=alarm_definition_id)
        resp, response_body = self.monasca_client.list_alarms(query_param)
        self._verify_list_alarms_elements(resp, response_body,
                                          expect_num_elements=4)
        elements = response_body['elements']
        dimensions = []
        for i in xrange(4):
            self.assertEqual(len(elements[i]['metrics']), 1)
            dimensions.append(elements[i]['metrics'][0]['dimensions'])
        for i in xrange(4):
            for j in xrange(4):
                if i != j:
                    self.assertNotEqual(dimensions[i], dimensions[j])

        self.monasca_client.delete_alarm_definition(alarm_definition_id)

    def _verify_list_alarms_elements(self, resp, response_body,
                                     expect_num_elements=None):
        self.assertEqual(200, resp.status)
        self.assertTrue(set(['links', 'elements']) ==
                        set(response_body))
        if expect_num_elements:
            error_msg = ("Failed: {} alarm is needed and current number "
                         "of alarm is {}").format(expect_num_elements,
                                                  len(response_body['elements']))
            self.assertEqual(len(response_body['elements']),
                             expect_num_elements, error_msg)

    def _create_alarms_for_test_alarms(self, num):
        metric_name = data_utils.rand_name('name')
        key = data_utils.rand_name('key')
        value = data_utils.rand_name('value')
        alarm_definition_ids = []
        for i in xrange(num):
            # create an alarm definition
            expression = "avg(" + metric_name + ") > 0"
            name = data_utils.rand_name('name-1')
            alarm_definition = helpers.create_alarm_definition(
                name=name, expression=expression)
            resp, response_body = self.monasca_client.create_alarm_definitions(
                alarm_definition)
            alarm_definition_ids.append(response_body['id'])
        expected_metric = helpers.create_metric(name=metric_name,
                                                dimensions={key: value})
        # create some metrics
        alarms = []
        for j in xrange(num):
            self.monasca_client.create_metrics(expected_metric)
            for i in xrange(constants.MAX_RETRIES):
                time.sleep(constants.RETRY_WAIT_SECS)
                query_param = '?alarm_definition_id=' + \
                              str(alarm_definition_ids[j])
                resp, response_body = self.monasca_client.list_alarms(
                    query_param)
                elements = response_body['elements']
                if len(elements) >= 1:
                    alarms.extend(elements)
                    break
        return alarms

    def _create_metrics_for_match_by(self, num, alarm_definition_id):
        metric1 = helpers.create_metric(
            name='cpu.idle_perc',
            dimensions={'service': 'monitoring',
                        'hostname': 'mini-mon'})
        metric2 = helpers.create_metric(
            name='cpu.idle_perc',
            dimensions={'service': 'monitoring',
                        'hostname': 'devstack'})
        self.monasca_client.create_metrics(metric1)
        self.monasca_client.create_metrics(metric2)
        self._waiting_for_alarms(num, alarm_definition_id)

    def _create_metrics_for_match_by_sub_expressions(self, num,
                                                     alarm_definition_id):
        metric1 = helpers.create_metric(
            name='cpu.idle_perc',
            dimensions={'service': 'monitoring',
                        'hostname': 'mini-mon'})
        metric2 = helpers.create_metric(
            name='cpu.idle_perc',
            dimensions={'service': 'monitoring',
                        'hostname': 'devstack'})
        self.monasca_client.create_metrics(metric1)
        self.monasca_client.create_metrics(metric2)
        metric3 = helpers.create_metric(
            name='cpu.user_perc',
            dimensions={'service': 'monitoring',
                        'hostname': 'mini-mon'})
        metric4 = helpers.create_metric(
            name='cpu.user_perc',
            dimensions={'service': 'monitoring',
                        'hostname': 'devstack'})
        self.monasca_client.create_metrics(metric3)
        self.monasca_client.create_metrics(metric4)
        self._waiting_for_alarms(num, alarm_definition_id)

    def _create_metrics_for_match_by_sub_expressions_list(self, num,
                                                          alarm_definition_id):
        # create some metrics
        metric1 = helpers.create_metric(
            name='cpu.idle_perc',
            dimensions={'service': 'monitoring',
                        'hostname': 'mini-mon',
                        'device': '/dev/sda1'})
        metric2 = helpers.create_metric(
            name='cpu.idle_perc',
            dimensions={'service': 'monitoring',
                        'hostname': 'devstack',
                        'device': '/dev/sda1'})
        metric3 = helpers.create_metric(
            name='cpu.idle_perc',
            dimensions={'service': 'monitoring',
                        'hostname': 'mini-mon',
                        'device': 'tmpfs'})
        metric4 = helpers.create_metric(
            name='cpu.idle_perc',
            dimensions={'service': 'monitoring',
                        'hostname': 'devstack',
                        'device': 'tmpfs'})
        self.monasca_client.create_metrics(metric1)
        self.monasca_client.create_metrics(metric2)
        self.monasca_client.create_metrics(metric3)
        self.monasca_client.create_metrics(metric4)
        self._waiting_for_alarms(num, alarm_definition_id)

    def _waiting_for_alarms(self, num, alarm_definition_id):
        query_param = '?alarm_definition_id=' + str(alarm_definition_id)
        for i in xrange(constants.MAX_RETRIES):
            time.sleep(constants.RETRY_WAIT_SECS)
            resp, response_body = self.monasca_client.\
                list_alarms(query_param)
            elements = response_body['elements']
            if len(elements) >= num:
                break

    def _verify_alarm_keys(self, response_body):
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

    def _verify_metric_in_alarm(self, metric, expected_metric):
        self.assertEqual(metric['dimensions'], expected_metric['dimensions'])
        self.assertEqual(metric['name'], expected_metric['name'])
