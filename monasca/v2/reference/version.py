# Copyright 2015 Hewlett-Packard
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
from oslo.config import cfg

from monasca.common.messaging import exceptions as message_queue_exceptions
from monasca.common import resource_api
from monasca.openstack.common import log
from monasca.v2.reference import helpers

LOG = log.getLogger(__name__)


class Version(object):
    def __init__(self):

        try:

            self._region = cfg.CONF.region

            self._default_authorized_roles = (
                cfg.CONF.security.default_authorized_roles)
            self._delegate_authorized_roles = (
                cfg.CONF.security.delegate_authorized_roles)
            self._post_metrics_authorized_roles = (
                cfg.CONF.security.default_authorized_roles +
                cfg.CONF.security.agent_authorized_roles)

        except Exception as ex:
            LOG.exception(ex)
            raise falcon.HTTPInternalServerError('Service unavailable',
                                                 ex.message)

    def _send_version(self, version):
        try:
            self._message_queue.send_message_batch(version)
        except message_queue_exceptions.MessageQueueException as ex:
            LOG.exception(ex)
            raise falcon.HTTPServiceUnavailable('Service unavailable', ex.message, 60)

    @resource_api.Restify('/', method='get')
    def do_get_version(self, req, res):
        result = {u'links': [{u'rel': u'self', u'href': req.uri.decode('utf8')}], u'elements': [{
            u'id': 'v2.0', u'links': [{u'rel': u'self', u'href': req.uri.decode('utf8') + 'v2.0'}],
            u'status': 'CURRENT', u'updated': '2015-05-19T19:21:00Z'}]}
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_200
