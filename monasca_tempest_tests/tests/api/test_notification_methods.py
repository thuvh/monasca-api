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

# TODO(RMH): Validate whether a 200 or 201 should be returned and resolve.
# TODO(RMH): Documentation says 200, but a 201 is being returned.

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import helpers
from tempest.common.utils import data_utils
from tempest import test
from tempest_lib import exceptions

DEFAULT_EMAIL_ADDRESS = 'john.doe@domain.com'


class TestNotificationMethods(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestNotificationMethods, cls).resource_setup()

    @test.attr(type="gate")
    def test_create_notification_method(self):
        notification = helpers.create_notification()
        resp, response_body = self.monasca_client.create_notifications(
            notification)
        self.assertEqual(201, resp.status)
        id = response_body['id']
        resp, response_body = self.monasca_client.\
            delete_notification_method(id)
        self.assertEqual(204, resp.status)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_create_notification_method_with_no_name(self):
        notification = helpers.create_notification(name=None)
        self.assertRaises(exceptions.UnprocessableEntity,
                          self.monasca_client.create_notifications,
                          notification)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_create_notification_method_invalid_chars_in_name(self):
        return

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_create_notification_method_name_exceeds_max_length(self):
        return

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_create_notification_method_address_exceeds_max_length(self):
        return

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_create_notification_method_with_invalid_type(self):
        return

    @test.attr(type="gate")
    def test_get_notification_method(self):
        notification = helpers.create_notification()
        resp, response_body = self.monasca_client.create_notifications(
            notification)
        self.assertEqual(201, resp.status)
        id = response_body['id']
        resp, response_body = self.monasca_client.get_notification_method(
            id)
        self.assertEqual(200, resp.status)
        resp, response_body = self.monasca_client.\
            delete_notification_method(id)
        self.assertEqual(204, resp.status)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_get_notification_method_with_invalid_id(self):
        return

    @test.attr(type="gate")
    def test_update_notification_method_name(self):
        name = data_utils.rand_name('notification-')
        notification = helpers.create_notification(name=name)
        resp, response_body = self.monasca_client.create_notifications(
            notification)
        self.assertEqual(201, resp.status)
        self.assertEqual(name, response_body['name'])
        id = response_body['id']
        new_name = name + 'update'
        resp, response_body = self.monasca_client.\
            update_notification_method(id, new_name,
                                       type=response_body['type'],
                                       address=response_body['address'])
        self.assertEqual(200, resp.status)
        self.assertEqual(new_name, response_body['name'])
        resp, response_body = self.monasca_client.\
            delete_notification_method(id)
        self.assertEqual(204, resp.status)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_update_notification_method_name_exceeds_max_length(self):
        return

    @test.attr(type="gate")
    def test_update_notification_method_type(self):
        type = 'EMAIL'
        notification = helpers.create_notification(type=type)
        resp, response_body = self.monasca_client.create_notifications(
            notification)
        self.assertEqual(201, resp.status)
        self.assertEqual(type, response_body['type'])
        id = response_body['id']
        new_type = 'PAGERDUTY'
        resp, response_body = \
            self.monasca_client.\
            update_notification_method(id, name=response_body['name'],
                                       type=new_type,
                                       address=response_body['address'])
        self.assertEqual(200, resp.status)
        self.assertEqual(new_type, response_body['type'])
        resp, response_body = self.monasca_client.\
            delete_notification_method(id)
        self.assertEqual(204, resp.status)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_update_notification_method_invalid_type(self):
        return

    @test.attr(type="gate")
    def test_update_notification_method_address(self):
        address = DEFAULT_EMAIL_ADDRESS
        notification = helpers.create_notification(address=address)
        resp, response_body = self.monasca_client.create_notifications(
            notification)
        self.assertEqual(201, resp.status)
        self.assertEqual(address, response_body['address'])
        id = response_body['id']
        new_address = 'jane.doe@domain.com'
        resp, response_body = self.monasca_client.\
            update_notification_method(id,
                                       name=response_body['name'],
                                       type=response_body['type'],
                                       address=new_address)
        self.assertEqual(200, resp.status)
        self.assertEqual(new_address, response_body['address'])
        resp, body = self.monasca_client.delete_notification_method(id)
        self.assertEqual(204, resp.status)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_update_notification_method_address_exceeds_max_length(self):
        return

    @test.attr(type="gate")
    def test_list_notification_methods(self):
        resp, body = self.monasca_client.list_notification_methods()
        self.assertEqual(200, resp.status)
        # TODO(RMH): Validate response body

    @test.attr(type="gate")
    def test_list_notification_methods_offset_limit(self):
        return
