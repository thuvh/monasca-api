# Copyright 2014 Hewlett-Packard
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
import json

import falcon

from monasca_api.api import versions_api
from monasca_api.openstack.common import log

LOG = log.getLogger(__name__)
VERSIONS = {
    u'v2.0': {
        u'id': 'v2.0',
        u'links': {
            u'rel': 'self',
            u'href': 'v2.0'
        },
        u'status': 'CURRENT',
        u'updated': "2013-03-06T00:00:00Z"
    }
}


class Versions(versions_api.VersionsAPI):

    def __init__(self):
        super(Versions, self).__init__()

    def on_get(self, req, res, version_id=None):
        result = {
            u'links': [],
            u'elements': []
            }
        links = {
            u'rel': 'self',
            u'href': req.uri.decode('utf8')
        }
        result[u'links'].append(links)
        if version_id is None:
            for version in VERSIONS:
                VERSIONS[version][u'links'][u'href'] = \
                    req.uri.decode('utf8') + \
                    VERSIONS[version][u'links'][u'href']
                result[u'elements'].append(VERSIONS[version])
            res.body = json.dumps(result)
            res.status = falcon.HTTP_200
        else:
            if version_id in VERSIONS:
                VERSIONS[version_id][u'links'][u'href'] = \
                    req.uri.decode('utf8')
                result[u'elements'].append(VERSIONS[version_id])
                res.body = json.dumps(result)
                res.status = falcon.HTTP_200
            else:
                res.body = 'Invalid Version ID'
                res.status = falcon.HTTP_400
