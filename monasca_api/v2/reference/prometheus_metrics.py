# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import falcon

from oslo_log import log
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import generate_latest

from monasca_api.api import prometheus_metrics_api, prometheus_registry

LOG = log.getLogger(__name__)


class PrometheusMetrics(prometheus_metrics_api.PrometheusMetricsAPI):
    skip_keystone_auth = True

    def __init__(self, registry=prometheus_registry.REGISTRY):
        super(PrometheusMetrics, self).__init__()
        self.registry = registry

    def on_get(self, req, res):
        try:
            latest = generate_latest(self.registry)

            res.content_type = CONTENT_TYPE_LATEST.encode('ascii')
            res.body = latest
            res.status = falcon.HTTP_200
        except:
            raise falcon.HTTPInternalServerError('Error generating '
                                                 'metric output')
