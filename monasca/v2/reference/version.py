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

from monasca.common import resource_api
from monasca.openstack.common import log
from monasca.v2.reference import helpers

LOG = log.getLogger(__name__)
currentVersion = 'v2.0'


class Version(object):

    @resource_api.Restify('/', method='get')
    def do_get_version(self, req, res):
        result = {u'links': [{
            u'rel': u'self', u'href': req.uri.decode('utf8')}],
            u'elements': [{
                u'id': currentVersion,
                u'links': [{
                    u'rel': u'self',
                    u'href': req.uri.decode('utf8') + currentVersion
                }],
            u'status': 'CURRENT', u'updated': '2015-05-19T19:21:00Z'}]}
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_200
