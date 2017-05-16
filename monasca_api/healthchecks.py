# Copyright 2017 FUJITSU LIMITED
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

from monasca_common.rest import utils as rest_utils

from monasca_api.api import healthcheck_api
from monasca_api.healtcheck import kafka_check,\
                                   relational_db_check,\
                                   timeseries_db_check


class HealthChecks(healthcheck_api.HealthCheckApi):

    CACHE_CONTROL = ['must-revalidate', 'no-cache', 'no-store']

    HEALTHY_CODE_GET = falcon.HTTP_OK
    HEALTHY_CODE_HEAD = falcon.HTTP_NO_CONTENT
    NOT_HEALTHY_CODE = falcon.HTTP_SERVICE_UNAVAILABLE

    def __init__(self):
        self._kafka_check = kafka_check.KafkaHealthHealthCheck()
        self._rel_db_check = relational_db_check.RelationalDbHealthCheck()
        self._time_db_check = timeseries_db_check.TimeseriesDbCheck()
        super(HealthChecks, self).__init__()

    def on_head(self, req, res):
        res.status = self.HEALTHY_CODE_HEAD
        res.cache_control = self.CACHE_CONTROL

    def on_get(self, req, res):
        kafka_result = self._kafka_check.health_check()
        relational_db_result = self._rel_db_check.health_check()
        timestamp_db_result = self._time_db_check.health_check()

        status_data = {
            'kafka': kafka_result.message,
            'relational_database': relational_db_result.message,
            'timestamp_database': timestamp_db_result.message
        }
        health = (kafka_result.health and relational_db_result.health and
                  timestamp_db_result.health)
        res.status = (self.HEALTHY_CODE_GET
                      if health else self.NOT_HEALTHY_CODE)
        res.cache_control = self.CACHE_CONTROL
        res.body = rest_utils.as_json(status_data)
