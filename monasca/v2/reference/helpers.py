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

import falcon
from falcon.util.uri import parse_query_string


def validate_json_content_type(req):
    if req.content_type not in ['application/json']:
        raise falcon.HTTPBadRequest('Bad request', 'Bad content type. Must be application/json')


def is_in_role(req, authorized_roles):
    str_roles = req.get_header('X-ROLES')
    if str_roles == None:
        return False
    roles = str_roles.lower().split(',')
    for role in roles:
        if role in authorized_roles:
            return True
    return False


def validate_authorization(req, authorized_roles):
    str_roles = req.get_header('X-ROLES')
    if str_roles == None:
        raise falcon.HTTPUnauthorized('Forbidden', 'Tenant does not have any roles', '')
    roles = str_roles.lower().split(',')
    for role in roles:
        if role in authorized_roles:
            return
    raise falcon.HTTPUnauthorized('Forbidden', 'Tenant ID is missing a required role to access this service', '')


def get_tenant_id(req):
    return req.get_header('X-TENANT-ID')


def get_cross_tenant_or_tenant_id(req, delegate_authorized_roles):
    if is_in_role(req, delegate_authorized_roles):
        params = parse_query_string(req.query_string)
        if 'tenant_id' in params:
            tenant_id = params['tenant_id']
            return tenant_id
    return get_tenant_id(req)