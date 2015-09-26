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


class TestMeasurements(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestMeasurements, cls).resource_setup()

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
    def test_list_measurements(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?name=name-1&merge_metrics=true&start_time=' + str(
            start_time)
        resp, response_body = self.monasca_client.list_measurements(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_list_measurements_with_no_start_time(self):
        query_parms = '?name=name-1'
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.list_measurements, query_parms)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_list_measurements_with_no_name(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?start_time=' + str(start_time)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.list_measurements, query_parms)

    @test.attr(type="gate")
    def test_list_measurements_with_name(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?name=name-1&merge_metrics=true&start_time=' + str(
            start_time)
        resp, response_body = self.monasca_client.list_measurements(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_measurements_with_dimensions(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?name=name-1&start_time=' + str(
            start_time) + '&dimensions=key1:value1'
        resp, response_body = self.monasca_client.list_measurements(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_measurements_with_endtime(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        end_time = timeutils.iso8601_from_timestamp(
            self._end_timestamp / 1000)
        query_parms = '?name=name-1&merge_metrics=true&true&start_time=' + str(
            start_time) + '&end_time' + str(end_time)
        resp, body = self.monasca_client.list_measurements(query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_measurements_with_offset_limit(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?name=name-1&merge_metrics=true&start_time=' + str(
            start_time) + '&offset=1&limit=2'
        resp, body = self.monasca_client.list_measurements(query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_measurements_with_merge_metrics(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?name=name-1&merge_metrics=true&start_time=' + str(
            start_time)
        resp, response_body = self.monasca_client.list_measurements(
            query_parms)
        self.assertEqual(200, resp.status)

    @test.attr(type="gate")
    def test_list_measurements_with_name_exceeds_max_length(self):
        long_name = "x" * (constants.MAX_LIST_MEASUREMENTS_NAME_LENGTH + 1)
        start_time = timeutils.iso8601_from_timestamp(self._start_timestamp
                                                      / 1000)
        query_parms = '?name=' + str(long_name) \
                      + '&merge_metrics=true&start_time=' + str(start_time)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.list_measurements, query_parms)

    @test.attr(type="gate")
    def test_list_measurements_response_body(self):
        start_time = timeutils.iso8601_from_timestamp(
            self._start_timestamp / 1000)
        query_parms = '?name=name-1&merge_metrics=true&start_time=' + str(
            start_time)
        resp, response_body = self.monasca_client.list_measurements(
            query_parms)
        self.assertTrue(set(['links', 'elements']) == set(response_body))
        elements = response_body['elements']
        element = elements[0]
        self.assertTrue(set(['id', 'name', 'dimensions', 'columns',
                             'measurements']) == set(element))
        # check if 'id' is an unicode. NOPE its NoneType
        # self.assertTrue(type(element['id']) is None)
        # check if 'name' is string/unicode
        self.assertTrue(type(element['name']) is unicode)
        # check if 'dimensions' is dictionary {string: string}
        self.assertTrue(type(element['dimensions']) is dict)
        # check if 'columns' is a list
        self.assertTrue(type(element['columns']) is list)
        # check if 'measurements' is a list
        self.assertTrue(type(element['measurements']) is list)
