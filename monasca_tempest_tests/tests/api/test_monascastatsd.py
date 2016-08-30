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

from monasca_tempest_tests.tests.api import base
from monasca_tempest_tests.tests.api import constants
from tempest import test

import monascastatsd

class TestMonascaStatsd(base.BaseMonascaTest):

    @classmethod
    def resource_setup(cls):
        super(TestMonascaStatsd, cls).resource_setup()

    @classmethod
    def resource_cleanup(cls):
        super(TestMonascaStatsd, cls).resource_cleanup()

    @test.attr(type="gate")
    def test_basic_statsd(self):
        statsd = monascastatsd.Client(name='monasca')
        foo = statsd.get_gauge(name='Test|Test')
        foo.send('Test|Test', 1, dimensions={'A:B': 1, 'BC': 3})
        for timer in xrange(constants.MAX_RETRIES):
            resp, response_body = self.monasca_client.metrics.list(name='Test|Test.Test|Test')
            if resp not None:
                return
            else:
                time.sleep(constants.RETRY_WAIT_SECS)
        error_msg = "Failed test_basic_statsd: " \
                    "timeout on waiting for metric to show up in the api"
        self.fail(error_msg)
