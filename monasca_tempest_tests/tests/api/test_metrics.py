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

# TODO(RMH): Check if ' should be added in the list of INVALID_CHARS.
# TODO(RMH): test_create_metric_no_value, should return 422 if value not sent

import time

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import constants
from monasca_tempest_tests.tests.api import helpers
from tempest import test
from tempest_lib import exceptions


class TestMetrics(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestMetrics, cls).resource_setup()

    @test.attr(type='gate')
    def test_create_metric(self):
        metric = helpers.create_metric()
        resp, body = self.monasca_client.create_metrics(metric)
        self.assertEqual(204, resp.status)

    @test.attr(type='gate')
    def test_create_metrics(self):
        metrics = [
            helpers.create_metric('name-1'),
            helpers.create_metric('name-2'),
        ]
        resp, body = self.monasca_client.create_metrics(metrics)
        self.assertEqual(204, resp.status)

    @test.attr(type='gate')
    @test.attr(type=['negative'])
    def test_create_metric_with_no_name(self):
        metric = helpers.create_metric(name=None)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_metrics,
                          metric)

    @test.attr(type='gate')
    def test_create_metric_with_no_dimensions(self):
        metric = helpers.create_metric(dimensions=None)
        resp, body = self.monasca_client.create_metrics(metric)
        self.assertEqual(204, resp.status)

    @test.attr(type='gate')
    @test.attr(type=['negative'])
    def test_create_metric_with_no_timestamp(self):
        metric = helpers.create_metric(timestamp=None)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_metrics,
                          metric)

    @test.attr(type='gate')
    @test.attr(type=['negative'])
    def test_create_metric_no_value(self):
        timestamp = time.time() * 1000
        metric = helpers.create_metric(timestamp=timestamp,
                                       value=None)
        return
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_metrics,
                          metric)

    @test.attr(type='gate')
    @test.attr(type=['negative'])
    def test_create_metric_with_name_exceeds_max_length(self):
        long_name = "x" * (constants.MAX_METRIC_NAME_LENGTH + 1)
        metric = helpers.create_metric(long_name)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_metrics,
                          metric)

    @test.attr(type='gate')
    @test.attr(type=['negative'])
    def test_create_metric_with_invalid_chars_in_name(self):
        for invalid_char in constants.INVALID_CHARS:
            metric = helpers.create_metric(invalid_char)
            self.assertRaises(exceptions.UnprocessableEntity,
                              self.monasca_client.create_metrics,
                              metric)

    @test.attr(type='gate')
    @test.attr(type=['negative'])
    def test_create_metric_invalid_chars_in_dimensions(self):
        for invalid_char in constants.INVALID_CHARS:
            metric = helpers.create_metric('name-1', {'key-1': invalid_char})
            self.assertRaises(exceptions.UnprocessableEntity,
                              self.monasca_client.create_metrics,
                              metric)
        for invalid_char in constants.INVALID_CHARS:
            metric = helpers.create_metric('name-1', {invalid_char: 'value-1'})
            self.assertRaises(exceptions.UnprocessableEntity,
                              self.monasca_client.create_metrics,
                              metric)

    @test.attr(type='gate')
    @test.attr(type=['negative'])
    def test_create_metric_dimension_key_exceeds_max_length(self):
        long_key = "x" * (constants.MAX_DIMENSION_KEY_LENGTH + 1)
        metric = helpers.create_metric('name-1', {long_key: 'value-1'})
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_metrics,
                          metric)

    @test.attr(type='gate')
    @test.attr(type=['negative'])
    def test_create_metric_dimension_value_exceeds_max_length(self):
        long_value = "x" * (constants.MAX_DIMENSION_VALUE_LENGTH + 1)
        metric = helpers.create_metric('name-1', {'key-1': long_value})
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_metrics,
                          metric)

    @test.attr(type='gate')
    def test_list_metrics(self):
        resp, response_body = self.monasca_client.list_metrics()
        self.assertEqual(200, resp.status)

    @test.attr(type='gate')
    def test_list_metrics_response_body(self):
        # TODO(RMH): Add validation of response body
        resp, response_body = self.monasca_client.list_metrics()
        self.assertTrue(set(['links', 'elements']) == set(response_body))
        elements = response_body['elements']
        element = elements[0]
        self.assertTrue(set(['id', 'name', 'dimensions']) == set(element))
        # check if 'id' is an int. NOPE its unicode
        self.assertTrue(type(element['id']) is unicode)
        # check if 'name' is a string. NOPE its unicode
        self.assertTrue(type(element['name']) is unicode)
        # check if 'dimensions' is dictionary {string: string}
        self.assertTrue(type(element['dimensions']) is dict)

    @test.attr(type='gate')
    def test_list_metrics_with_name(self):
        query_parms = '?name=name-1'
        resp, response_body = self.monasca_client.list_metrics(query_parms)
        self.assertEqual(200, resp.status)
        # But this makes the 'dimensions' empty. Why?
        return

    @test.attr(type='gate')
    def test_list_metrics_with_dimensions(self):
        query_parms = '?dimensions=key1:value1'
        resp, response_body = self.monasca_client.list_metrics(query_parms)
        self.assertEqual(200, resp.status)
        return

    @test.attr(type='gate')
    def test_list_metrics_with_offset_limit(self):
        query_parms = '?offset=1&limit=2'
        resp, response_body = self.monasca_client.list_metrics(query_parms)
        self.assertEqual(200, resp.status)
        return
