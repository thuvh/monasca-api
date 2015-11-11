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
from tempest.common.utils import data_utils
from tempest import test
from tempest_lib import exceptions


class TestMetrics(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestMetrics, cls).resource_setup()
        name = data_utils.rand_name('name')
        key = data_utils.rand_name('key')
        value = data_utils.rand_name('value')
        timestamp = int(time.time() * 1000)
        time_iso = helpers.timestamp_to_time_iso(timestamp, microsecond=False)
        time_iso_millisecond = helpers.timestamp_to_time_iso_millisecond(
            timestamp, microsecond=True)
        metric_value = 1.23
        meta_key = data_utils.rand_name('meta_key')
        meta_value = data_utils.rand_name('meta_value')
        metric = helpers.create_metric(name=name,
                                       dimensions={key: value},
                                       timestamp=timestamp,
                                       value=metric_value,
                                       value_meta={meta_key: meta_value})
        cls._metric = metric
        cls._name = name
        cls._key = key
        cls._value = value
        cls._time_iso = time_iso

        timestamp2 = int(time.time() * 1000 + 6000)
        time_iso_millisecond2 = helpers.timestamp_to_time_iso_millisecond(
            timestamp2, microsecond=True)
        metric_value2 = 4.56
        meta_key2 = data_utils.rand_name('value_meta_key')
        meta_value2 = data_utils.rand_name('value_meta_value')

        metrics = [
            helpers.create_metric(name=name,
                                  dimensions={key: value},
                                  timestamp=timestamp,
                                  value=metric_value,
                                  value_meta={meta_key: meta_value}),
            helpers.create_metric(name=name,
                                  dimensions={key: value},
                                  timestamp=timestamp2,
                                  value=metric_value2,
                                  value_meta={meta_key2: meta_value2})
        ]
        cls._metrics = metrics
        cls._time_iso_millisecond = [time_iso_millisecond,
                                     time_iso_millisecond2]
        cls._metric_value = [metric_value, metric_value2]
        cls._meta_key = [meta_key, meta_key2]
        cls._meta_value = [meta_value, meta_value2]

    @classmethod
    def resource_cleanup(cls):
        super(TestMetrics, cls).resource_cleanup()

    @test.attr(type='gate')
    def test_create_metric(self):
        resp, response_body = self.monasca_client.create_metrics(self._metric)
        self.assertEqual(204, resp.status)
        query_param = '?name=' + self._name + '&start_time=' + self._time_iso
        for i in xrange(constants.MAX_RETRIES):
            resp, response_body = self.monasca_client.\
                list_measurements(query_param)
            self.assertEqual(200, resp.status)
            elements = response_body['elements']
            for element in elements:
                if str(element['name']) == self._name:
                    self.assertEqual(set(element),
                                     set(['columns', 'dimensions', 'id',
                                          'measurements', 'name']))
                    self.assertEqual(set(element['columns']),
                                     set(['timestamp', 'value', 'value_meta']))
                    self.assertEqual(str(element['dimensions'][self._key]),
                                     self._value)
                    self.assertEqual(str(element['id']),
                                     self._time_iso_millisecond[0])
                    measurement = element['measurements'][0]
                    self.assertEqual(str(measurement[0]),
                                     self._time_iso_millisecond[0])
                    self.assertEqual(measurement[1], self._metric_value[0])
                    self.assertEqual(str(measurement[2][self._meta_key[0]]),
                                     self._meta_value[0])
                    return
            time.sleep(constants.RETRY_TIMEOUT_SECS)
            if i == constants.MAX_RETRIES - 1:
                error_msg = "Failed test_create_metric: " \
                            "timeout on waiting for metrics: at least " \
                            "one metric is needed. Current number of " \
                            "metrics = 0"
                self.fail(error_msg)

    @test.attr(type='gate')
    def test_create_metrics(self):
        resp, response_body = self.monasca_client.create_metrics(self._metrics)
        self.assertEqual(204, resp.status)
        query_param = '?name=' + self._name + '&start_time=' + \
                      str(self._time_iso)
        for i in xrange(constants.MAX_RETRIES):
            resp, response_body = self.monasca_client.\
                list_measurements(query_param)
            self.assertEqual(200, resp.status)
            elements = response_body['elements']
            for element in elements:
                if str(element['name']) == self._name \
                        and len(element['measurements']) == 2:
                    self.assertEqual(set(element),
                                     set(['columns', 'dimensions', 'id',
                                          'measurements', 'name']))
                    self.assertEqual(set(element['columns']),
                                     set(['timestamp', 'value', 'value_meta']))
                    self.assertEqual(str(element['dimensions'][self._key]),
                                     self._value)
                    self.assertEqual(str(element['id']),
                                     self._time_iso_millisecond[1])
                    first_measurement = element['measurements'][0]
                    second_measurement = element['measurements'][1]
                    self.assertEqual(str(first_measurement[0]),
                                     self._time_iso_millisecond[0])
                    self.assertEqual(first_measurement[1], self._metric_value[0])
                    self.assertEqual(str(first_measurement[2][self._meta_key[0]]),
                                     self._meta_value[0])
                    self.assertEqual(str(second_measurement[0]),
                                     self._time_iso_millisecond[1])
                    self.assertEqual(second_measurement[1],
                                     self._metric_value[1])
                    self.assertEqual(str(second_measurement[2]
                                         [self._meta_key[1]]),
                                     self._meta_value[1])
                    return
            time.sleep(constants.RETRY_TIMEOUT_SECS)
            if i == constants.MAX_RETRIES - 1:
                error_msg = "Failed test_create_metrics: " \
                            "timeout on waiting for metrics: at least " \
                            "one metric is needed. Current number of " \
                            "metrics = 0"
                self.fail(error_msg)

    @test.attr(type='gate')
    @test.attr(type=['negative'])
    def test_create_metric_with_no_name(self):
        metric = helpers.create_metric(name=None)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_metrics,
                          metric)

    @test.attr(type='gate')
    def test_create_metric_with_no_dimensions(self):
        name = data_utils.rand_name('name')
        timestamp = int(time.time() * 1000)
        time_iso = helpers.timestamp_to_time_iso(timestamp, microsecond=False)
        time_iso_millisecond = helpers.timestamp_to_time_iso_millisecond(
            timestamp, microsecond=True)
        metric_value = 1.23
        meta_key = data_utils.rand_name('value_meta_key')
        meta_value = data_utils.rand_name('value_meta_value')
        metric = helpers.create_metric(name=name,
                                       dimensions=None,
                                       timestamp=timestamp,
                                       value=metric_value,
                                       value_meta={meta_key: meta_value})
        resp, response_body = self.monasca_client.create_metrics(metric)
        self.assertEqual(204, resp.status)
        query_param = '?name=' + str(name) + '&start_time=' + str(time_iso)
        for i in xrange(constants.MAX_RETRIES):
            resp, response_body = self.monasca_client.\
                list_measurements(query_param)
            self.assertEqual(200, resp.status)
            elements = response_body['elements']
            for element in elements:
                if str(element['name']) == name:
                    self.assertEqual(element['dimensions'], {})
                    self.assertEqual(str(element['id']), time_iso_millisecond)
                    self.assertEqual(str(element['measurements'][0][0]),
                                     time_iso_millisecond)
                    self.assertEqual(element['measurements'][0][1],
                                     metric_value)
                    self.assertEqual(str(element['measurements'][0][2]
                                         [meta_key]),
                                     meta_value)
                    return
            time.sleep(constants.RETRY_TIMEOUT_SECS)
            if i == constants.MAX_RETRIES - 1:
                error_msg = "Failed test_create_metric_with_no_dimensions: " \
                            "timeout on waiting for metrics: at least " \
                            "one metric is needed. Current number of " \
                            "metrics = 0"
                self.fail(error_msg)

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
    def test_create_metric_with_invalid_chars_in_dimensions(self):
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
        self.assertTrue(set(['links', 'elements']) == set(response_body))
        elements = response_body['elements']
        element = elements[0]
        self.assertTrue(set(['id', 'name', 'dimensions']) == set(element))
        self.assertTrue(type(element['id']) is unicode)
        self.assertTrue(type(element['name']) is unicode)
        self.assertTrue(type(element['dimensions']) is dict)

    @test.attr(type='gate')
    def test_list_metrics_with_dimensions(self):
        name = data_utils.rand_name('name')
        key = data_utils.rand_name('key')
        value = data_utils.rand_name('value')
        metric = helpers.create_metric(name=name,
                                       dimensions={key: value})
        resp, response_body = self.monasca_client.create_metrics(metric)
        self.assertEqual(204, resp.status)
        query_param = '?dimensions=' + key + ':' + value
        for i in xrange(constants.MAX_RETRIES):
            resp, response_body = self.monasca_client.\
                list_metrics(query_param)
            self.assertEqual(200, resp.status)
            elements = response_body['elements']
            for element in elements:
                if str(element['dimensions'][key]) == value:
                    self.assertEqual(str(element['id']), '0')
                    self.assertEqual(str(element['name']), name)
                    return
            time.sleep(constants.RETRY_TIMEOUT_SECS)
            if i == constants.MAX_RETRIES - 1:
                error_msg = "Failed test_list_metrics_with_dimensions: " \
                            "timeout on waiting for metrics: at least " \
                            "one metric is needed. Current number of " \
                            "metrics = 0"
                self.fail(error_msg)

    @test.attr(type='gate')
    def test_list_metrics_with_name(self):
        name = data_utils.rand_name('name')
        key = data_utils.rand_name('key')
        value = data_utils.rand_name('value')
        metric = helpers.create_metric(name=name,
                                       dimensions={key: value})
        resp, response_body = self.monasca_client.create_metrics(metric)
        self.assertEqual(204, resp.status)
        query_param = '?name=' + str(name)
        for i in xrange(constants.MAX_RETRIES):
            resp, response_body = self.monasca_client.\
                list_metrics(query_param)
            self.assertEqual(200, resp.status)
            elements = response_body['elements']
            for element in elements:
                if str(element['name']) == name:
                    self.assertEqual(set(element),
                                     set(['dimensions', 'id', 'name']))
                    self.assertEqual(str(element['dimensions'][key]), value)
                    self.assertEqual(str(element['id']), '0')
                    return
            time.sleep(constants.RETRY_TIMEOUT_SECS)
            if i == constants.MAX_RETRIES - 1:
                error_msg = "Failed test_list_metrics_with_name: " \
                            "timeout on waiting for metrics: at least " \
                            "one metric is needed. Current number of " \
                            "metrics = 0"
                self.fail(error_msg)

    @test.attr(type='gate')
    def test_list_metrics_with_offset_limit(self):
        name = data_utils.rand_name()
        key1 = data_utils.rand_name()
        key2 = data_utils.rand_name()

        metrics = [
            helpers.create_metric(name=name, dimensions={
                key1: 'value-1', key2: 'value-1'}),
            helpers.create_metric(name=name, dimensions={
                key1: 'value-2', key2: 'value-2'}),
            helpers.create_metric(name=name, dimensions={
                key1: 'value-3', key2: 'value-3'}),
            helpers.create_metric(name=name, dimensions={
                key1: 'value-4', key2: 'value-4'})
        ]
        self.monasca_client.create_metrics(metrics)
        query_param = '?name=' + name
        for i in xrange(constants.MAX_RETRIES):
            resp, response_body = self.monasca_client.list_metrics(query_param)
            elements = response_body['elements']
            if elements and len(elements) == 4:
                break
            time.sleep(constants.RETRY_TIMEOUT_SECS)
            if i == constants.MAX_RETRIES - 1:
                error_msg = ("Failed test_list_metrics_with_offset_limit: "
                             "timeout on waiting for metrics: 4 metrics "
                             "are needed. Current number of elements = "
                             "{}").format(len(elements))
                self.fail(error_msg)

        first_element = elements[0]
        last_element = elements[3]
        query_parms = '?name=' + name + '&limit=4'
        resp, response_body = self.monasca_client.list_metrics(query_parms)
        self.assertEqual(200, resp.status)
        elements = response_body['elements']
        self.assertEqual(4, len(elements))
        self.assertEqual(first_element, elements[0])
        timeout = time.time() + constants.ONE_MINUTE_TIME_OUT
        for limit in xrange(1, 5):
            next_element = elements[limit - 1]
            while True:
                if time.time() >= timeout:
                    msg = "Failed test_list_metrics_with_offset_limit: one " \
                          "minute timeout on offset limit test loop"
                    raise exceptions.TimeoutException(msg)
                else:
                    query_parms = '?name=' + name + '&offset=' + \
                                  str(next_element['id']) + '&limit=' + \
                                  str(limit)
                    resp, response_body = self.\
                        monasca_client.list_metrics(query_parms)
                    self.assertEqual(200, resp.status)
                    new_elements = response_body['elements']

                    if len(new_elements) > limit - 1:
                        self.assertEqual(limit, len(new_elements))
                        next_element = new_elements[limit - 1]
                    elif 0 < len(new_elements) <= limit - 1:
                        self.assertEqual(last_element, new_elements[0])
                        break
                    else:
                        self.assertEqual(last_element, next_element)
                        break
