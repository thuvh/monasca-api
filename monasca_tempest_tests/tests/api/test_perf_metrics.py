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

import multiprocessing
import time

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import constants
from monasca_tempest_tests.tests.api import helpers
from tempest.common.utils import data_utils
from tempest import test

num_metrics = 50
num_processes = 10
num_requests = 4
total_metrics = num_processes * num_requests * num_metrics

max_wait_time = 30
timestamp_delta = 10

TARGET_NUM_METRICS = 100


class TestPerfMetrics(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestPerfMetrics, cls).resource_setup()
        cls.num_calls = 0

    @classmethod
    def resource_cleanup(cls):
        super(TestPerfMetrics, cls).resource_cleanup()

    @test.attr(type='perf')
    def test_metric_perf(self):
        name_metric_perf = data_utils.rand_name('metric_perf')
        sent_q = multiprocessing.Queue()
        process_list = []
        first_time = time.time()
        for i in xrange(num_processes):
            p = multiprocessing.Process(
                target=self._create_metrics_process(
                    process_num=i, queue=sent_q,
                    name=name_metric_perf, first_time=first_time))
            process_list.append(p)
        start_time = time.time()
        start_time_iso = \
            helpers.timestamp_to_iso(int(round(start_time * 1000)))
        end_time_iso = \
            helpers.timestamp_to_iso(
                int(round((start_time + 3600 * 24) * 1000)))  # one day after
        for p in process_list:
            p.start()
        for p in process_list:
            p.join()

        total_metrics_sent = 0
        while not sent_q.empty():
            item = sent_q.get()
            total_metrics_sent += item

        metrics_found = 0
        last_count = 0
        last_change = time.time()
        while metrics_found < total_metrics_sent:
            query_parms = '?name=' + str(name_metric_perf) + \
                          '&start_time=' + start_time_iso + \
                          '&end_time=' + end_time_iso + \
                          '&merge_metrics=True&statistics=count&period=1000000'
            resp, response_body = self.monasca_client.list_statistics(
                query_parms)
            self.assertEqual(200, resp.status)
            elements = response_body['elements']
            if len(elements) > 0:
                metrics_found = elements[0]['statistics'][0][1]
            if metrics_found > last_count:
                last_change = time.time()
                last_count = metrics_found
            if (last_change + max_wait_time) <= time.time():
                error_msg = ("Max wait time exceeded, {0} / {1} metrics found."
                             ).format(metrics_found, total_metrics_sent)
                self.fail(error_msg)
            time.sleep(constants.RETRY_WAIT_SECS)

        final_time = time.time()
        total_time = final_time - start_time
        num_metric_per_second = metrics_found / total_time
        fail_msg = ("Failed test_metric_perf, num_metric_per_second = {0} "
                    "and target number = {1}").format(num_metric_per_second,
                                                      TARGET_NUM_METRICS)
        self.assertGreaterEqual(num_metric_per_second, TARGET_NUM_METRICS,
                                fail_msg)

    def _create_metrics_process(self, process_num, queue, name,
                                first_time):
        for x in xrange(num_requests):
            body = []
            for k in xrange(num_metrics):
                metric = helpers.create_metric(
                    name=name,
                    dimensions={"dim": "agent-" + str(process_num)},
                    timestamp=int(round(first_time * 1000 + self.num_calls *
                                        timestamp_delta)),
                    value=self.num_calls)
                self.num_calls += 1
                body.append(metric)
            self.monasca_client.create_metrics(body)
            if queue:
                queue.put(num_metrics)
