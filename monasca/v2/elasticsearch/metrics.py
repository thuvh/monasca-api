# Copyright 2013 IBM Corp
#
# Author: Tong Li <litong01@us.ibm.com>
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

import falcon
from oslo.config import cfg

from monasca.common import resource_api
from monasca.openstack.common import log
from monasca.v2.elasticsearch import base

metrics_opts = [
    cfg.StrOpt('topic', default='metrics',
               help='The topic that metrics will be published to.'),
]

metrics_group = cfg.OptGroup(name='metrics', title='metrics')
cfg.CONF.register_group(metrics_group)
cfg.CONF.register_opts(metrics_opts, metrics_group)

LOG = log.getLogger(__name__)


class MetricDispatcher(base.BaseDispatcher):
    def __init__(self, global_conf):
        LOG.debug('initializing V2API!')
        super(MetricDispatcher, self).__init__(global_conf,
                                               cfg.CONF.metrics.topic)

    @resource_api.Restify('/v2.0/metrics/', method='get')
    def do_get_metrics(self, req, res):
        LOG.debug('Got the request!')
        res.status = getattr(falcon, 'HTTP_501')

    @resource_api.Restify('/v2.0/metrics/', method='post')
    def do_post_metrics(self, req, res):
        self.post_data(req, res)

    @resource_api.Restify('/v2.0/metrics/measurements', method='get')
    def do_get_measurements(self, req, res):
        res.status = getattr(falcon, 'HTTP_501')

    @resource_api.Restify('/v2.0/metrics/statistics', method='get')
    def do_get_statistics(self, req, res):
        res.status = getattr(falcon, 'HTTP_501')