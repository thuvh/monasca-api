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
"""
Auth Middleware Module.

"""

from oslo.middleware import request_id
from oslo.serialization import jsonutils
import webob.dec
import webob.exc

from monasca.middleware import context, wsgi
from monasca.openstack.common import log

LOG = log.getLogger(__name__)


class InjectContext(wsgi.Middleware):
    """Add a 'monasca.context' to WSGI environ."""

    def __init__(self, context, *args, **kwargs):
        self.context = context
        super(InjectContext, self).__init__(*args, **kwargs)

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        req.environ['monasca.context'] = self.context
        return self.application


class MonascaKeystoneContext(wsgi.Middleware):
    """Make a request context from keystone headers."""

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):

        user_id = req.headers.get('X_USER')
        user_id = req.headers.get('X_USER_ID', user_id)
        if user_id is None:
            LOG.error("Neither X_USER_ID nor X_USER found in request")
            return webob.exc.HTTPUnauthorized()

        roles = self._get_roles(req)

        project_id = req.headers['X_PROJECT_ID']
        project_name = req.headers.get('X_PROJECT_NAME')

        domain_id = req.headers['X_DOMAIN_ID']
        domain_name = req.headers.get('X_DOMAIN_NAME')

        user_name = req.headers.get('X_USER_NAME')

        req_id = req.environ.get(request_id.ENV_REQUEST_ID)

        # Get the auth token
        auth_token = req.headers.get('X_AUTH_TOKEN',
                                     req.headers.get('X_STORAGE_TOKEN'))

        service_catalog = None
        if req.headers.get('X_SERVICE_CATALOG') is not None:
            try:
                catalog_header = req.headers.get('X_SERVICE_CATALOG')
                service_catalog = jsonutils.loads(catalog_header)
            except ValueError:
                raise webob.exc.HTTPInternalServerError('Invalid service catalog json.')


        # NOTE(jamielennox): This is a full auth plugin set by auth_token
        # middleware in newer versions.
        user_auth_plugin = req.environ.get('keystone.token_auth')



        # Build a context
        ctx = context.RequestContext(user_id,
                                     project_id,
                                     user_name=user_name,
                                     project_name=project_name,
                                     domain_id=domain_id,
                                     domain_name=domain_name,
                                     roles=roles,
                                     auth_token=auth_token,
                                     service_catalog=service_catalog,
                                     request_id=req_id,
                                     user_auth_plugin=user_auth_plugin)

        req.environ['monasca.context'] = ctx
        return self.application

    def _get_roles(self, req):
        """Get the list of roles."""

        if 'X_ROLES' in req.headers:
            roles = req.headers.get('X_ROLES', '')
        else:
            # Fallback to deprecated role header:
            roles = req.headers.get('X_ROLE', '')
            if roles:
                LOG.warning("Sourcing roles from deprecated X-Role HTTP "
                             "header")
        return [r.strip() for r in roles.split(',')]
