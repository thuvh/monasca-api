# Copyright 2018 Hewlett Packard Enterprise Development Company, L.P.
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

from monasca_api.tests import base
from monasca_api.v2.common.exceptions import HTTPUnprocessableEntityError
from monasca_api.v2.reference import helpers

ONE_MINUTE = 60 * 1000
ONE_WEEK = 7 * 24 * 60 * 60 * 1000

class TestValidateTimestampRange(base.BaseTestCase):

    def test_validate_timestamp_range(self):
        timestamp = time.time() * 1000
        metric = {'timestamp': timestamp}
        try:
            helpers.validate_timestamp_range(metric, should_validate=True,
                                             future_seconds=ONE_MINUTE,
                                             past_seconds=ONE_WEEK)
        except HTTPUnprocessableEntityError:
            self.fail("Test validate timestamp failed.")

    def test_validate_timestamp_range_invalid_future(self):
        timestamp = time.time() * 1000 + ONE_MINUTE * 2
        metric = {'timestamp': timestamp}
        try:
            helpers.validate_timestamp_range(metric, should_validate=True,
                                             future_seconds=ONE_MINUTE,
                                             past_seconds=ONE_WEEK)
        except HTTPUnprocessableEntityError:
            pass
        else:
            self.fail("Test validate timestamp should have failed with"
                      " HTTPUnprocessableEntityError.")

    def test_validate_timestamp_range_invalid_past(self):
        timestamp = time.time() * 1000 - ONE_WEEK
        metric = {'timestamp': timestamp}
        try:
            helpers.validate_timestamp_range(metric, should_validate=True,
                                             future_seconds=ONE_MINUTE,
                                             past_seconds=ONE_WEEK)
        except HTTPUnprocessableEntityError:
            pass
        else:
            self.fail("Test validate timestamp should have failed with"
                      " HTTPUnprocessableEntityError.")

    def test_validate_timestamp_range_turn_off(self):
        timestamp = time.time() * 1000 + ONE_MINUTE * 2  # Invalid future time
        metric = {'timestamp': timestamp}
        try:
            helpers.validate_timestamp_range(metric, should_validate=False,
                                             future_seconds=ONE_MINUTE,
                                             past_seconds=ONE_WEEK)
        except HTTPUnprocessableEntityError:
            self.fail("Test validate timestamp failed. "
                      "Configured flag should skip validation")