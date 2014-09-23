# Copyright 2014 Hewlett-Packard
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

from oslo.config import cfg
from monasca.common.messaging import publisher
from monasca.common.messaging import kafka_publisher
from monasca.common.messaging import rabbitmq_publisher


def create_publisher(type):
    message_queue = cfg.CONF.messaging.message_queue

    if message_queue == 'kafka':
        if type == "metrics":
            topic = cfg.CONF.kafka.metrics_topic
        elif type == "events":
            topic = cfg.CONF.kafka.events_topic
        else:
            raise Exception("Unsupported type %s" % type)

        return kafka_publisher.KafkaPublisher(topic)

    elif message_queue == 'rabbitmq':
        return rabbitmq_publisher.RabbitmqPublisher()
    else:
        return publisher.Publisher()