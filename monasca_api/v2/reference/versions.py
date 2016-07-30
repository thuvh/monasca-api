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

import six

import falcon
from oslo_log import log

from monasca_api.api import versions_api
from monasca_api.v2.common.exceptions import HTTPUnprocessableEntityError

LOG = log.getLogger(__name__)
VERSIONS = {
    'v2.0': {
        'id': 'v2.0',
        'links': [{
            'rel': 'self',
            'href': ''
        }],
        'status': 'CURRENT',
        'updated': "2013-03-06T00:00:00.000Z"
    }
}


class Versions(versions_api.VersionsAPI):
    def __init__(self):
        super(Versions, self).__init__()

    def on_get(self, req, res, version_id=None):
        path = req.uri
        if six.PY2 and isinstance(req.uri, six.text_type):
            path = path.decode('utf=8')

        result = {
            'links': [{
                'rel': 'self',
                'href': path
            }],
            'elements': []
        }
        if version_id is None:
            for version in VERSIONS:
                VERSIONS[version]['links'][0]['href'] = (
                    path + version)
                result['elements'].append(VERSIONS[version])
            res.body = json.dumps(result)
            res.status = falcon.HTTP_200
        else:
            if version_id in VERSIONS:
                VERSIONS[version_id]['links'][0]['href'] = (
                    path)
                res.body = json.dumps(VERSIONS[version_id])
                res.status = falcon.HTTP_200
            else:
                raise HTTPUnprocessableEntityError('Invalid version',
                                                   'No versions found matching ' + version_id)
