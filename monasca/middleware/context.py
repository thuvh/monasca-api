# Copyright (c) 2014 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""RequestContext: context for requests that persist through monasca."""

import uuid

from oslo.utils import timeutils
import six

from monasca.openstack.common import log

LOG = log.getLogger(__name__)


class RequestContext(object):
    """Security context and request information.

    Represents the user taking a given action within the system.

    """

    def __init__(self, user_id, project_id, domain_id=None, domain_name=None,
                 roles=None, timestamp=None, request_id=None,
                 auth_token=None, user_name=None, project_name=None,
                 service_catalog=None, user_auth_plugin=None, **kwargs):
        """Creates the Keystone Context. Supports additional parameters:

        :param user_auth_plugin:
            The auth plugin for the current request's authentication data.
        :param kwargs:
            Extra arguments that might be present
        """
        if kwargs:
            LOG.warning(
                'Arguments dropped when creating context: %s') % str(kwargs)

        self.roles = roles or []
        if not timestamp:
            timestamp = timeutils.utcnow()
        if isinstance(timestamp, six.string_types):
            timestamp = timeutils.parse_strtime(timestamp)
        self.timestamp = timestamp

        if not request_id:
            request_id = self.generate_request_id()
        self.request_id = request_id
        self.auth_token = auth_token

        if service_catalog:
            # Only include required parts of service_catalog
            self.service_catalog = [s for s in service_catalog
                                    if s.get('type') in ('volume', 'volumev2')]
        else:
            # if list is empty or none
            self.service_catalog = []

        self.domain_id = domain_id
        self.domain_name = domain_name

        self.user_id = user_id
        self.user_name = user_name

        self.project_id = project_id
        self.project_name = project_name

        self.user_auth_plugin = user_auth_plugin

    def to_dict(self):
        return {'user_id': self.user_id,
                'project_id': self.project_id,
                'domain_id': self.domain_id,
                'domain_name': self.domain_name,
                'roles': self.roles,
                'timestamp': timeutils.strtime(self.timestamp),
                'request_id': self.request_id,
                'auth_token': self.auth_token,
                'user_name': self.user_name,
                'service_catalog': self.service_catalog,
                'project_name': self.project_name,
                'user': self.user}

    def generate_request_id(self):
        return b'req-' + str(uuid.uuid4()).encode('ascii')

    @classmethod
    def from_dict(cls, values):
        values.pop('user', None)
        values.pop('tenant', None)
        return cls(**values)
