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

from oslo_config import cfg
from oslo_log import log

from monasca_api.healtcheck import base
from monasca_common.kafka_lib import client

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class KafkaHealthHealthCheck(base.BaseHealthCheck):

    def health_check(self):
        url = CONF.kafka.uri

        try:
            kafka_client = client.KafkaClient(hosts=url)
        except client.KafkaUnavailableError as ex:
            LOG.error(repr(ex))
            error_str = 'Could not connect to Kafka at {0}'.format(url)
            return base.CheckResult(health=False, message=error_str)

        result = self._verify_topics(kafka_client)
        self._disconnect_gracefully(kafka_client)

        return result

    @staticmethod
    def _verify_topics(kafka_client):
        topics = CONF.kafka.metrics_topic

        for topic in topics:
            for_topic = topic in kafka_client.topic_partitions
            if not for_topic:
                error_str = 'Kafka: Topic {0} not found'.format(for_topic)
                LOG.error(error_str)
                return base.CheckResult(health=False, message=error_str)
        return base.CheckResult(health=True, message='OK')

    @staticmethod
    def _disconnect_gracefully(kafka_client):
        try:
            kafka_client.close()
        except Exception as ex:
            LOG.exception(str(ex))
