# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP
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

import six.moves.urllib.parse as urlparse

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import helpers
from tempest import test
from tempest.lib import exceptions

from monasca_tempest_tests import clients

class TestReadOnlyRole(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestReadOnlyRole, cls).resource_setup()
        credentials = cls.cred_provider.get_creds_by_roles(
            ['monasca-read-only-user']).credentials
        cls.os = clients.Manager(credentials=credentials)
        cls.monasca_client = cls.os.monasca_client

    @classmethod
    def resource_cleanup(cls):
        super(TestReadOnlyRole, cls).resource_cleanup()

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_delete_alarms_fails(self):
        self.assertRaises(exceptions.Unauthorized,
                          self.monasca_client.delete_alarm, "foo")

    @test.attr(type='gate')
    @test.attr(type=['negative'])
    def test_create_metric_fails(self):
        self.assertRaises(exceptions.Unauthorized,
                          self.monasca_client.create_metrics,
                          None)

    @test.attr(type="gate")
    @test.attr(type=['negative'])
    def test_create_alarm_definition_fails(self):
        self.assertRaises(exceptions.Unauthorized,
                          self.monasca_client.create_alarm_definitions,
                          None)
