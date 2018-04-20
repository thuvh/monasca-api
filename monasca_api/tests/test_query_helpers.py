# Copyright 2015 Cray Inc. All Rights Reserved.
# Copyright 2016 Hewlett Packard Enterprise Development Company, L.P.
# Copyright 2017 Fujitsu LIMITED
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

from mock import Mock

from monasca_api.tests import base
from monasca_api.v2.reference import helpers


class TestGetOldQueryParams(base.BaseTestCase):

    def test_old_query_params(self):
        uri = Mock()
        uri.query = "foo=bar&spam=ham"

        result = helpers._get_old_query_params(uri)
        self.assertEqual(result, ["foo=bar", "spam=ham"])

    def test_old_query_params_with_equals(self):
        uri = Mock()
        uri.query = "foo=spam=ham"

        result = helpers._get_old_query_params(uri)
        self.assertEqual(result, ["foo=spam%3Dham"])

    def test_old_query_params_except_offset(self):
        uri = Mock()
        uri.query = "foo=bar&spam=ham"
        result = []

        helpers._get_old_query_params_except_offset(result, uri)
        self.assertEqual(result, ["foo=bar", "spam=ham"])

    def test_old_query_params_except_offset_with_equals(self):
        uri = Mock()
        uri.query = "foo=spam=ham&offset=bar"
        result = []

        helpers._get_old_query_params_except_offset(result, uri)
        self.assertEqual(result, ["foo=spam%3Dham"])
