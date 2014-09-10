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
from kafka import client
from kafka import common
from kafka import producer
from oslo.config import cfg
import time
import ujson as json

from monasca.common import resource_api
from monasca.openstack.common import log


OPTS = [
    cfg.StrOpt('uri',
               help='Address to kafka server. For example: '
               'uri=192.168.1.191:9092'),
    cfg.StrOpt('topic',
               default='event',
               help='The topic that this dispatcher will post to.'),
    cfg.IntOpt('max_retry',
               default=3,
               help='The max times the dispatcher will try to post'),
    cfg.BoolOpt('async',
                default=True,
                help='The type of posting.'),
    cfg.BoolOpt('compact',
                default=True,
                help=('Specify if the message received should be parsed.'
                      'If True, message will not be parsed, otherwise '
                      'messages will be parsed.')),
    cfg.BoolOpt('drop_data',
                default=False,
                help=('Specify if received data should be simply dropped. '
                      'This parameter is only for testing purposes.')),
]

cfg.CONF.register_opts(OPTS, group="kafka")


LOG = log.getLogger(__name__)


class KafkaDispatcher(object):
    def __init__(self, global_conf):
        LOG.debug('initializing KafkaDispatcher!')

        self.global_conf = global_conf
        self.uri = cfg.CONF.kafka.uri
        self.drop_data = cfg.CONF.kafka.drop_data
        self.topic = cfg.CONF.kafka.topic
        self.max_retry = cfg.CONF.kafka.max_retry
        self.async = cfg.CONF.kafka.async
        self.compact = cfg.CONF.kafka.compact

        self.client = None
        self.producer = None

    def _init_kafka(self):
        if self.uri:
            try:
                if self.client:
                    self.client.close()
                self.client = client.KafkaClient(self.uri)
                self.producer = producer.SimpleProducer(self.client,
                                                        async=self.async,
                                                        ack_timeout=20)
                LOG.debug("Successfully connected to Kafka server!")
            except (common.KafkaUnavailableError, AttributeError,
                    Exception):
                LOG.exception('Error occurred while connecting to Kafka.')
        else:
            LOG.error("Kafka server is not configured. Please use the "
                      "parameter uri, topic, max_retry, etc to "
                      "configure kafka. Restart the server once it is "
                      "configured.")

    @resource_api.Restify(path='/v2.0/metrics', method='post')
    def on_post_metrics(self, req, res):
        LOG.debug('Getting the call.')
        msg = ''
        while True:
            chunk = req.stream.read(1024)
            if not chunk:
                break
            msg = msg.join(chunk)

        if msg:
            if self.drop_data:
                res.status = falcon.HTTP_204
            else:
                if not self.client or not self.producer:
                    self._init_kafka()
                for i in range(0, self.max_retry):
                    try:
                        LOG.debug('Start sending messages to kafka.')
                        if self.compact:
                            self.producer.send_messages(self.topic, msg)
                        else:
                            data = json.loads(msg)
                            LOG.debug('Msg parsed successfully.')
                            if isinstance(data, list):
                                for item in data:
                                    self.producer.send_messages(
                                        self.topic, json.dumps(item))
                            else:
                                self.producer.send_messages(self.topic, msg)
                        res.status = falcon.HTTP_204
                        LOG.debug('Message posted successfully.')
                        break
                    except ValueError:
                        LOG.exception('Message is not valid json.')
                        res.status = falcon.HTTP_406
                        break
                    except (common.KafkaUnavailableError, AttributeError,
                            Exception):
                        LOG.exception('Error occurred while posting data to '
                                      'Kafka.')
                        res.status = falcon.HTTP_503
                        time.sleep(0.1)
                        self._init_kafka()
