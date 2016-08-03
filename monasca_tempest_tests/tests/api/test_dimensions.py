# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
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
from tempest.common.utils import data_utils
from tempest import test
from tempest.lib import exceptions


class TestDimensions(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestDimensions, cls).resource_setup()
        metric_name1 = data_utils.rand_name()
        name1 = "name_1"
        name2 = "name_2"
        value1 = "value_1"
        value2 = "value_2"

        metric1 = helpers.create_metric(name=metric_name1,
                                        dimensions={name1: value1,
                                                    name2: value2
                                                    })
        cls.monasca_client.create_metrics(metric1)
        metric1 = helpers.create_metric(name=metric_name1,
                                        dimensions={name1: value2})
        cls.monasca_client.create_metrics(metric1)
        cls._test_metric1 = metric1

        metric_name2 = data_utils.rand_name()
        name3 = "name_3"
        value3 = "value_3"
        metric2 = helpers.create_metric(name=metric_name2,
                                        dimensions={name3: value3})
        cls.monasca_client.create_metrics(metric2)
        cls._test_metric2 = metric2
        cls._test_metric_names = set([metric_name1, metric_name2])
        cls._dim_names_metric1 = [name1, name2]
        cls._dim_names_metric2 = [name3]
        cls._dim_names = cls._dim_names_metric1 + cls._dim_names_metric2
        cls._dim_values = [value1, value2]
        start_time = str(timeutils.iso8601_from_timestamp(
                         metric1['timestamp'] / 1000.0))

        param = '?start_time=' + start_time
        returned_name_set = set()
        for i in xrange(constants.MAX_RETRIES):
            resp, response_body = cls.monasca_client.list_metrics(
                param)
            elements = response_body['elements']
            for element in elements:
                returned_name_set.add(str(element['name']))
            if cls._test_metric_names.issubset(returned_name_set):
                return
            time.sleep(constants.RETRY_WAIT_SECS)

        assert False, 'Unable to initialize metrics'

    @classmethod
    def resource_cleanup(cls):
        super(TestDimensions, cls).resource_cleanup()

    @test.attr(type='gate')
    def test_list_dimension_values_without_metric_name(self):
        param = '?dimension_name=' + self._dim_names[0]
        resp, response_body = self.monasca_client.list_dimension_values(param)
        self.assertEqual(200, resp.status)
        self.assertTrue(set(['links', 'elements']) == set(response_body))
        if not self._is_dimension_name_in_list(response_body,
                                               self._dim_names[0]):
            self.fail('Dimension name {} not found in response'.
                      format(self._dim_names[0]))
        if not self._is_metric_name_not_in_list(response_body):
            self.fail('Metric name was in response and should not be')
        response_values = response_body['elements'][0]['values']
        values = [str(value) for value in response_values]
        self.assertEqual(values, self._dim_values)

    @test.attr(type='gate')
    def test_list_dimension_values_with_metric_name(self):
        parms = '?metric_name=' + self._test_metric1['name']
        parms += '&dimension_name=' + self._dim_names[0]
        resp, response_body = self.monasca_client.list_dimension_values(parms)
        self.assertEqual(200, resp.status)
        self.assertTrue(set(['links', 'elements']) == set(response_body))
        if not self._is_metric_name_in_list(response_body,
                                            self._test_metric1['name']):
            self.fail('Metric name not found in response')
        if not self._is_dimension_name_in_list(response_body,
                                               self._dim_names[0]):
            self.fail('Dimension name {} not found in response'.
                      format(self._dim_names[0]))
        response_values = response_body['elements'][0]['values']
        values = [str(value) for value in response_values]
        self.assertEqual(values, self._dim_values)

    @test.attr(type='gate')
    def test_list_dimension_values_limit_and_offset(self):
        limit = 1
        parms = '?dimension_name=' + self._dim_names[0]
        parms += '&limit={}'.format(limit)
        resp, response_body = self.monasca_client.list_dimension_values(parms)
        self.assertEqual(200, resp.status)
        self.assertTrue(set(['links', 'elements']) == set(response_body))
        if not self._is_dimension_name_in_list(response_body,
                                               self._dim_names[0]):
            self.fail('Dimension name {} not found in response'.
                      format(self._dim_names[0]))
        response_values = response_body['elements'][0]['values']
        values = [str(value) for value in response_values]
        self.assertEqual(values, [self._dim_values[0]])
        if not self._is_offset_in_links(response_body, self._dim_values[0]):
            self.fail('Offset not found in response')
        if not self._is_limit_in_links(response_body, limit):
            self.fail('Limit not found in response')

    @test.attr(type='gate')
    @test.attr(type=['negative'])
    def test_list_dimension_values_no_dimension_name(self):
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.list_dimension_values)

    @test.attr(type='gate')
    def test_list_dimension_names(self):
        resp, response_body = self.monasca_client.list_dimension_names()
        self.assertEqual(200, resp.status)
        self.assertTrue(set(['links', 'elements']) == set(response_body))
        if not self._is_metric_name_not_in_list(response_body):
            self.fail('Metric name was in response and should not be')
        response_names = response_body['elements'][0]['dimension_names']
        names = [str(value) for value in response_names]
        self.assertEqual(names, self._dim_names)

    @test.attr(type='gate')
    def test_list_dimension_names_with_metric_name(self):
        self._test_list_dimension_names_with_metric_name(
            self._test_metric1['name'], self._dim_names_metric1)
        self._test_list_dimension_names_with_metric_name(
            self._test_metric2['name'], self._dim_names_metric2)

    @test.attr(type='gate')
    def test_list_dimension_names_limit_and_offset(self):
        limit = 1
        for i in xrange(2):
            offset = self._dim_names[i]
            parms = '?offset={}'.format(offset)
            parms += '&limit={}'.format(limit)
            resp, response_body = \
                self.monasca_client.list_dimension_names(parms)
            self.assertEqual(200, resp.status)
            self.assertTrue(set(['links', 'elements']) == set(response_body))

            response_names = response_body['elements'][0]['dimension_names']
            names = [str(name) for name in response_names]
            self.assertEqual(names, [self._dim_names[i + 1]])
            if not self._is_offset_in_links(response_body, self._dim_names[i]):
                self.fail('Offset not found in response')
            if not self._is_limit_in_links(response_body, limit):
                self.fail('Limit not found in response')

    def _test_list_dimension_names_with_metric_name(self, metric_name,
                                                    dimension_names):
        param = '?metric_name=' + metric_name
        resp, response_body = self.monasca_client.list_dimension_names(param)
        self.assertEqual(200, resp.status)
        self.assertTrue(set(['links', 'elements']) == set(response_body))
        if self._is_metric_name_not_in_list(response_body):
            self.fail('Metric name not found in response')
        self.assertEqual(metric_name,
                         response_body['elements'][0]['metric_name'])
        response_names = response_body['elements'][0]['dimension_names']
        names = [str(value) for value in response_names]
        self.assertEqual(names, dimension_names)

    def _is_metric_name_in_list(self, response_body, metric_name):
        elements = response_body['elements'][0]
        if 'metric_name' not in elements:
            return False
        if str(elements['metric_name']) == metric_name:
            return True
        return False

    def _is_metric_name_not_in_list(self, response_body):
        elements = response_body['elements'][0]
        if 'metric_name' not in elements:
            return True
        return False

    def _is_dimension_name_in_list(self, response_body, dimension_name):
        elements = response_body['elements'][0]
        if str(elements['dimension_name']) == dimension_name:
            return True
        return False

    def _are_dim_vals_in_list(self, response_body):
        element = response_body['elements'][0]
        have_dim_1 = self._is_dim_val_in_list(element, self._dim_values[0])
        have_dim_2 = self._is_dim_val_in_list(element, self._dim_values[1])
        if have_dim_1 and have_dim_2:
            return True
        return False

    def _is_dim_val_in_list(self, element, dim_val):
        if dim_val in element['values']:
            return True
        return False

    def _is_offset_in_links(self, response_body, dim_val):
        links = response_body['links']
        offset = "offset=" + dim_val
        for link in links:
            if offset in link['href']:
                return True
        return False

    def _is_limit_in_links(self, response_body, limit):
        links = response_body['links']
        for link in links:
            if str(limit) in link['href']:
                return True
        return False
