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
import numpy as np
import random
import time

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import constants
from monasca_tempest_tests.tests.api import helpers
from tempest import test

NUM_TRIALS = 10
NUM_METRICS_PER_TRIAL = 100
THRESH_ENGINE_EVAL_PERIOD_SECS = 60
COLLECTION_PERIOD_SECS = 35
METRIC_NAME = 'process_status'
ALARM_NAME = 'process_status'
ALARM_EXPRESSION = 'max(process_status{}, 60) > 0'
TARGET_MEAN = 30


class TestAlarmTransitionTimes(base.BaseMonascaTest):
    @classmethod
    def resource_setup(cls):
        super(TestAlarmTransitionTimes, cls).resource_setup()

    @classmethod
    def resource_cleanup(cls):
        super(TestAlarmTransitionTimes, cls).resource_cleanup()

    @test.attr(type="perf")
    def test_alarm_transition_times(self):
        # create an alarm definition
        alarm_definition = helpers.create_alarm_definition(
            name=ALARM_NAME, expression=ALARM_EXPRESSION, match_by=['id'])
        resp, response_body = self.monasca_client.create_alarm_definitions(
            alarm_definition)
        alarm_definition_id = response_body['id']
        metrics = []
        for i in xrange(NUM_METRICS_PER_TRIAL):
            metric = helpers.create_metric(name=METRIC_NAME,
                                           dimensions={'id': str(i)},
                                           timestamp=int(time.time()) * 1000,
                                           value=0.0)
            metrics.append(metric)
        self.monasca_client.create_metrics(metrics)

        for i in xrange(constants.MAX_RETRIES):
            query_param = '?alarm_definition_id=' + str(alarm_definition_id)
            resp, response_body = self.monasca_client.list_alarms(query_param)
            elements = response_body['elements']
            if elements:
                if len(elements) == 100:
                    break
                time.sleep(constants.RETRY_WAIT_SECS)

        means = [None] * NUM_TRIALS
        medians = [None] * NUM_TRIALS
        stds = [None] * NUM_TRIALS

        for trial in xrange(NUM_TRIALS):
            # Wait for all alarms to transition to OK
            self._wait_for_all_alarms_to_transition('OK')

            # Wait for 120 seconds + a random amount of time to give threshold
            # engine time to reach steady-state
            start_time = time.time()
            wait_time = 120 + random.randint(
                0, THRESH_ENGINE_EVAL_PERIOD_SECS - 1)
            while True:
                metrics = []
                for i in xrange(NUM_METRICS_PER_TRIAL):
                    metric = helpers.create_metric(name=METRIC_NAME,
                                                   dimensions={'id': str(i)},
                                                   value=0.0,
                                                   timestamp=int(time.time()) *
                                                   1000)
                    metrics.append(metric)
                self.monasca_client.create_metrics(metrics)
                current_time = time.time()
                if current_time > start_time + wait_time:
                    break
                time.sleep(constants.RETRY_WAIT_SECS)

            # Create random transition times for metrics in the
            # THRESHOLD_ENGINE_EVALUATION_PERIOD
            start_time = time.time()
            start_transition_times = \
                [start_time +
                 random.randint(0, THRESH_ENGINE_EVAL_PERIOD_SECS - 1)
                 for i in xrange(NUM_METRICS_PER_TRIAL)]
            end_transition_times = [None] * NUM_METRICS_PER_TRIAL
            metric_values = [0.0] * NUM_METRICS_PER_TRIAL

            # Transition metrics based on random transition times
            count = 0
            last_collection_time = time.time() - COLLECTION_PERIOD_SECS
            while True:
                current_time = time.time()
                metric_values = map(
                    lambda x: 1.0 if current_time >= x else 0.0,
                    start_transition_times)
                metrics = []
                for id_num in xrange(NUM_METRICS_PER_TRIAL):
                    metric = helpers.create_metric(
                        name=METRIC_NAME,
                        dimensions={'id': str(id_num)},
                        value=metric_values[id_num],
                        timestamp=int(time.time()) * 1000)
                    metrics.append(metric)
                if current_time >= \
                        (last_collection_time + COLLECTION_PERIOD_SECS):
                    self.monasca_client.create_metrics(metrics)
                    last_collection_time = current_time
                query_param = '?metric_name=' + str(METRIC_NAME)
                resp, response_body = \
                    self.monasca_client.list_alarms(query_param)
                alarms = response_body['elements']
                transitioned = [None] * NUM_METRICS_PER_TRIAL

                for alarm in alarms:
                    metric = alarm['metrics'][0]
                    dimensions = metric['dimensions']
                    id_num = int(dimensions['id'])
                    transitioned[id_num] = True if alarm['state'] == 'ALARM' \
                        else False
                end_transition_times = \
                    map(lambda x, y: time.time() if x and y is None else y,
                        transitioned, end_transition_times)
                all_transitioned = reduce(lambda x, y: x and y, transitioned)
                if all_transitioned:
                    break
                count += 1
                time.sleep(constants.RETRY_WAIT_SECS)

            # Evaluate statistics
            elapsed_times = map(lambda x, y: x - y, end_transition_times,
                                start_transition_times)
            mean = np.mean(elapsed_times)
            median = np.median(elapsed_times)
            std = np.std(elapsed_times)

            # Output statistics
            means[trial] = mean
            medians[trial] = median
            stds[trial] = std

        mean_of_means = np.mean(means)
        # mean_of_medians = np.mean(medians)
        # mean_of_stds = np.mean(stds)

        self.assertLessEqual(mean_of_means, TARGET_MEAN)

    def _wait_for_all_alarms_to_transition(self, state):
        all_transitioned = False
        while not all_transitioned:
            metrics = []
            for i in xrange(NUM_METRICS_PER_TRIAL):
                metric = helpers.create_metric(name=METRIC_NAME,
                                               dimensions={'id': str(i)},
                                               timestamp=int(time.time()) *
                                               1000,
                                               value=0.0)
                metrics.append(metric)
            self.monasca_client.create_metrics(metrics)
            query_param = '?metric_name=' + str(METRIC_NAME)
            resp, response_body = self.monasca_client.list_alarms(
                query_param)
            alarms = response_body['elements']
            transitioned = map(lambda x: x['state'] == state, alarms)
            if transitioned:
                all_transitioned = reduce(lambda x, y: x and y,
                                          transitioned)
            time.sleep(constants.RETRY_WAIT_SECS)
