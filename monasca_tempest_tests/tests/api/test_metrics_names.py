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

from monasca_tempest_tests.tests.api import base
from tempest import test


class TestMetricsNames(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestMetricsNames, cls).resource_setup()

    @test.attr(type='gate')
    def test_list_metrics_names(self):
        return

    @test.attr(type='gate')
    def test_list_metrics_names_with_dimensions(self):
        return

    @test.attr(type='gate')
    def test_list_metrics_names_with_offset_limit(self):
        return
