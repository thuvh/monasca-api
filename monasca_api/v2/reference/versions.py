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

from debtcollector import removals
import falcon

from monasca_api.api import versions_api
from monasca_api.v2.common.exceptions import HTTPUnprocessableEntityError
from monasca_api.v2.reference import helpers

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

    def on_get(self, req, res, version_id=None):
        result = {
            'links': [{
                'rel': 'self',
                'href': req.uri.decode('utf8')
            }],
            'elements': []
        }
        if version_id is None:
            for version in VERSIONS:
                VERSIONS[version]['links'][0]['href'] = (
                    req.uri.decode('utf8') + version)
                result['elements'].append(VERSIONS[version])
            res.body = helpers.to_json(result)
            res.status = falcon.HTTP_200
        else:
            if version_id in VERSIONS:
                VERSIONS[version_id]['links'][0]['href'] = (
                    req.uri.decode('utf8'))
                res.body = helpers.to_json(VERSIONS[version_id])
                res.status = falcon.HTTP_200
            else:
                raise HTTPUnprocessableEntityError('Invalid version',
                                                   'No versions found matching ' + version_id)


# NOTE(trebskit) this endpoint is kept only for sake of the
# backward compatibility and thus will be removed in the future
# in overall endpoint version (the one created from the class above)
# is available without the need of the authorization unlike the one
# created below
@removals.removed_class(
    cls_name='VersionV2',
    replacement='Versions',
    message='"VersionV2" is the version endpoint available only with '
            'Keystone token. That is not aligned with the rest of '
            'monasca where version endpoint are available without '
            'the need of obtaining the Keystone token.',
    version='2.2.0',
    removal_version='3.0.0'
)
class VersionV2(Versions):

    def on_get(self, req, res):
        super(VersionV2, self).on_get(req, res, 'v2.0')
