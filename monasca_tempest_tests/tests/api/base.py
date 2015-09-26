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

from monasca_tempest_tests.tests.api import helpers
from tempest.common.utils import data_utils
from tempest import config
import tempest.test
from tempest_lib import exceptions

from monasca_tempest_tests import clients

CONF = config.CONF


class BaseMonascaTest(tempest.test.BaseTestCase):
    """Base test case class for all Monasca API tests."""

    @classmethod
    def skip_checks(cls):
        super(BaseMonascaTest, cls).skip_checks()

    @classmethod
    def resource_setup(cls):
        super(BaseMonascaTest, cls).resource_setup()
        cls.os = clients.Manager()
        cls.monasca_client = cls.os.monasca_client

    @staticmethod
    def cleanup_resources(method, list_of_ids):
        for resource_id in list_of_ids:
            try:
                method(resource_id)
            except exceptions.NotFound:
                pass

    @classmethod
    def resource_cleanup(cls):
        super(BaseMonascaTest, cls).resource_cleanup()
        resp, response_body = cls.monasca_client.list_alarm_definitions()
        elements = response_body['elements']
        for definition in elements:
            id = definition['id']
            resp, response_body = cls.monasca_client. \
                delete_alarm_definition(id)

    @classmethod
    def create_alarms_for_test_alarms(cls):
        # create an alarm definition
        expression = "avg(name-1) > 0"
        name = data_utils.rand_name('name-1')
        alarm_definition = helpers.create_alarm_definition(
            name=name, expression=expression)
        resp, response_body = cls.monasca_client.create_alarm_definitions(
            alarm_definition)
        # create some metrics
        for i in xrange(30):
            metric = helpers.create_metric()
            resp, response_body = cls.monasca_client.create_metrics(metric)
            time.sleep(1)
            resp, response_body = cls.monasca_client.list_alarms()
            elements = response_body['elements']
            if len(elements) > 0:
                break

    @classmethod
    def create_alarms_for_test_alarms_state_history(cls):
        start_timestamp = int(time.time() * 1000)
        end_timestamp = int(time.time() * 1000) + 1000

        # create an alarm definition
        expression = "avg(name-1) > 0"
        name = data_utils.rand_name('name-1')
        alarm_definition = helpers.create_alarm_definition(
            name=name,
            expression=expression)
        resp, response_body = cls.monasca_client.create_alarm_definitions(
            alarm_definition)

        # create some metrics
        for i in xrange(180):
            metric = helpers.create_metric()
            resp, body = cls.monasca_client.create_metrics(metric)
            cls._start_timestamp = start_timestamp + i
            cls._end_timestamp = end_timestamp + i
            time.sleep(1)
            resp, response_body = cls.monasca_client.\
                list_alarms_state_history()
            elements = response_body['elements']
            if len(elements) > 0:
                break
