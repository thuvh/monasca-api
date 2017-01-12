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

from prometheus_client import Summary

TOTAL_REQUESTS = Summary('monasca_api_total_requests',
                         'Count and time for all requests',
                         ['_aggregate'])


def filter_factory(global_config, **local_conf):
    def instrument_filter(app):
        return PrometheusInstrumentationFilter(app, local_conf)

    return instrument_filter


class PrometheusInstrumentationFilter(object):
    def __init__(self, app, local_conf):
        self.app = app
        self.local_conf = local_conf

    def __call__(self, env, start_response):
        with TOTAL_REQUESTS.labels('sum').time():
            return self.app(env, start_response)
