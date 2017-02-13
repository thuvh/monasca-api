# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
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
import six

from oslo_log import log

LOG = log.getLogger(__name__)


def validate_authorization(req, authorized_roles):
    """Validates whether one or more X-ROLES in the HTTP header is authorized.

    If authorization fails, 401 is thrown with appropriate description.
    Additionally response specifies 'WWW-Authenticate' header with 'Token'
    value challenging the client to use different token (the one with
    different set of roles).

    :param req: HTTP request object. Must contain "X-ROLES" in the HTTP
    request header.
    :param authorized_roles: List of authorized roles to check against.
    :raises falcon.HTTPUnauthorized
    """
    roles = req.roles
    challenge = 'Token'
    if not roles:
        raise falcon.HTTPUnauthorized('Forbidden',
                                      'Tenant does not have any roles',
                                      challenge)
    roles = roles.split(',') if isinstance(roles, six.string_types) else roles
    authorized_roles_lower = [r.lower() for r in authorized_roles]
    for role in roles:
        role = role.lower()
        if role in authorized_roles_lower:
            return
    raise falcon.HTTPUnauthorized('Forbidden',
                                  'Tenant ID is missing a required role to '
                                  'access this service',
                                  challenge)


def get_x_tenant_or_tenant_id(req, delegate_authorized_roles):
    """Evaluates whether the tenant ID or cross tenant ID should be returned.

    :param req: HTTP request object.
    :param delegate_authorized_roles: List of authorized roles that have
    delegate privileges.
    :returns: Returns the cross tenant or tenant ID.
    """
    if any(x in set(delegate_authorized_roles) for x in req.roles):
        tenant_id = req.get_param('tenant_id')
        if tenant_id is not None:
            return tenant_id
    return req.project_id


class Authorize(object):
    def __init__(self, authorized_roles=None, delegate_authorized_roles=None):
        if authorized_roles is None:
            authorized_roles = []
        if delegate_authorized_roles is None:
            delegate_authorized_roles = []
        self.authorized_roles = authorized_roles
        self.delegate_authorized_roles = delegate_authorized_roles

    def __call__(self, fun):
        def wrapper(*args, **kwargs):
            req = args[1]
            validate_authorization(req, self.authorized_roles)
            req.tenant_id = get_x_tenant_or_tenant_id(req, self.delegate_authorized_roles)
            return fun(*args, **kwargs)
        return wrapper
