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

import time

from oslo_utils import timeutils

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import constants
from monasca_tempest_tests.tests.api import helpers
from tempest import test
from tempest_lib import exceptions

NUM_MEASUREMENTS = 100


class TestStatistics(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestStatistics, cls).resource_setup()

        start_timestamp = int(time.time() * 1000)
        end_timestamp = int(time.time() * 1000) + NUM_MEASUREMENTS * 1000
        metrics = []

        for i in xrange(NUM_MEASUREMENTS):
            metric = helpers.create_metric(
                name="name-1",
                timestamp=start_timestamp + i)
            metrics.append(metric)

        resp, response_body = cls.monasca_client.create_metrics(metric)
        cls._start_timestamp = start_timestamp
        cls._end_timestamp = end_timestamp
        cls._metrics = metrics

    @test.attr(type="gate")
    def test_list_statistics(self):
        start_time = timeutils.iso8601_from_timestamp(self._start_timestamp /
                                                      1000)
        query_parms = '?name=name-1&statistics=avg&start_time=' + str(
            start_time)
        resp, response_body = self.monasca_client.list_statistics(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_list_statistics_with_no_name(self):
        start_time = timeutils.iso8601_from_timestamp(self._start_timestamp /
                                                      1000)
        query_parms = '?statistics=avg&start_time=' + str(start_time)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.list_statistics, query_parms)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_list_statistics_with_no_statistics(self):
        start_time = timeutils.iso8601_from_timestamp(self._start_timestamp /
                                                      1000)
        query_parms = '?name=name-1&start_time=' + str(start_time)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.list_statistics, query_parms)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_list_statistics_with_no_start_time(self):
        query_parms = '?name=name-1&statistics=avg'
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.list_statistics, query_parms)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_list_statistics_with_invalid_statistics(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?name=name-1&statistics=abc&start_time=' + str(
            start_time)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.list_statistics, query_parms)

    @test.attr(type="gate")
    def test_list_statistics_with_dimensions(self):
        start_time = timeutils.iso8601_from_timestamp(self._start_timestamp
                                                      / 1000)
        query_parms = '?name=name-1&statistics=avg&start_time=' + str(
            start_time) + '&dimensions=key1:value1'
        resp, response_body = self.monasca_client.list_statistics(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_statistics_with_end_time(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        end_time = timeutils.iso8601_from_timestamp(
            self._end_timestamp / 1000)
        query_parms = '?name=name-1&statistics=avg&start_time=' + str(
            start_time) + '&end_time=' + str(end_time)
        resp, response_body = self.monasca_client.list_statistics(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_statistics_with_period(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?name=name-1&statistics=avg&start_time=' + str(
            start_time) + '&period=300'
        resp, response_body = self.monasca_client.list_statistics(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_statistics_with_offset_limit(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?name=name-1&statistics=avg&start_time=' + str(
            start_time) + '&offset=1&limit=2'
        resp, response_body = self.monasca_client.list_statistics(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_statistics_with_merge_metrics(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?name=name-1&statistics=avg&merge_metrics=true' \
                      '&start_time=' + str(start_time)
        resp, response_body = self.monasca_client.list_statistics(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_list_statistics_with_name_exceeds_max_length(self):
        long_name = "x" * (constants.MAX_LIST_STATISTICS_NAME_LENGTH + 1)
        start_time = timeutils.iso8601_from_timestamp(self._start_timestamp
                                                      / 1000)
        query_parms = '?name=' + str(long_name) + '&start_time=' + str(
            start_time)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.list_statistics, query_parms)

    @test.attr(type="gate")
    def test_list_statistics_response_body(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?statistics=avg&name=name-1&start_time=' + str(
            start_time)
        resp, response_body = self.monasca_client.list_statistics(
            query_parms)
        self.assertTrue(set(['links', 'elements']) == set(response_body))
        elements = response_body['elements']
        element = elements[0]
        self.assertTrue(set(['id', 'name', 'dimensions', 'columns',
                             'statistics']) == set(element))
        # check if 'id' is unicode type
        self.assertTrue(type(element['id']) is unicode)
        # check if 'name' is a string. NOPE its unicode
        self.assertTrue(type(element['name']) is unicode)
        self.assertTrue(type(element['dimensions']) is dict)
        self.assertTrue(type(element['columns']) is list)
        self.assertTrue(type(element['statistics']) is list)
        statistic = element['statistics']
        column = element['columns']
        self.assertTrue(type(statistic) is list)
        self.assertTrue(type(column) is list)

    @test.attr(type="gate")
    def test_list_statistics_with_more_than_one_statistics(self):
        start_time = timeutils.iso8601_from_timestamp(self._start_timestamp
                                                      / 1000)
        query_parms = '?name=name-1&statistics=avg,min,max&start_time=' + str(
            start_time)
        resp, response_body = self.monasca_client.list_statistics(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_statistics_response_body_statistic_result_type(self):
        start_time = timeutils.iso8601_from_timestamp(self._start_timestamp
                                                      / 1000)
        query_parms = '?name=name-1&statistics=avg&start_time=' + str(
            start_time)
        resp, response_body = self.monasca_client.list_statistics(
            query_parms)
        self.assertEqual(200, resp.status)
        element = response_body['elements'][0]
        statistic = element['statistics']
        statistic_result_type = type(statistic[0][1])
        self.assertEqual(statistic_result_type, float)
