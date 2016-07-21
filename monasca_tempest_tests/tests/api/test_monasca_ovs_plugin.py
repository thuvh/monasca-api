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
from monasca_tempest_tests.tests.api import helpers
from tempest import test
from tempest.api.network import base as tempest_base
from tempest import config

VROUTER_METRICS = ['vrouter.in_bytes', 'vrouter.out_bytes',
                   'vrouter.in_packets', 'vrouter.out_packets',
                   'vrouter.in_dropped', 'vrouter.out_dropped',
                   'vrouter.in_errors', 'vrouter.out_errors']

CONF = config.CONF


class TestOvsPlugin(base.BaseMonascaTest, tempest_base.BaseAdminNetworkTest):
    # Test measurements list for vrouter metrics for the ovs plugin
    # Validate each of the dimensions attributes in the response.

    @classmethod
    def resource_setup(cls):
        super(TestOvsPlugin, cls).resource_setup()
        start_timestamp = int(time.time() * 1000)
        start_time = str(helpers.timestamp_to_iso(start_timestamp))
        metrics = []
        time.sleep(120)
        end_timestamp = int(time.time() * 1000)
        end_time = str(helpers.timestamp_to_iso(end_timestamp))
        cls._start_time = start_time
        cls._end_time = end_time

    def _verify_list_metrics(self, resp, response_body):
        self.assertEqual(200, resp.status)
        self.assertTrue(set(['links', 'elements']) == set(response_body))

    def _get_gateway_router_id(self):
        # Fetch one router from the already created routers by tempest
        list_body = self.admin_routers_client.list_routers()
        routers_list = list()
        for router in list_body['routers']:
            routers_list.append(router['id'])
        if router['id'] is not None:
            return router['id']

    def _get_gateway_port_id(self, router_id):
        # Fetch the gateway ports
        list_body = self.admin_ports_client.list_ports(
            network_id=CONF.network.public_network_id,
            device_id=router_id)
        for port in list_body['ports']:
            port_id = port['id']
        if port_id is not None:
            return port_id

    def _verify_metrics(self, router_id, port_id, dimensions):
        # Validate each of the metrics paramters
        self.assertEqual(router_id, dimensions['resource_id'])
        self.assertEqual(port_id, dimensions['port_id'])
        self.assertEqual("ovs", dimensions['component'])
        self.assertEqual("networking", dimensions['service'])

    @test.attr(type="gate")
    def test_vrouter_metrics(self):
        # Test each of the vrouter metrics associated
        router_id = self._get_gateway_router_id()
        port_id = self._get_gateway_port_id(router_id)
        for name in VROUTER_METRICS:
            query_parms = '?name=' + str(name) + \
                          '&dimensions=port_id%3A' + str(port_id) + \
                          '&start_time=' + str(self._start_time) + \
                          '&end_time=' + str(self._end_time)
            resp, response_body = self.monasca_client.list_measurements(
                                  query_parms)
            self.assertTrue(str(response_body['elements'][0]) is not None)
            self._verify_list_metrics(resp, response_body)
            for element in response_body['elements']:
                dimensions = element['dimensions']
            self._verify_metrics(router_id, port_id, dimensions)
