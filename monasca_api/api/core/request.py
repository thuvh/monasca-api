# Copyright 2016 FUJITSU LIMITED
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
import iso8601
from oslo_context import context

from monasca_api.common import exceptions
from monasca_api.common.repositories import constants

_TENANT_ID_PARAM = 'tenant_id'
"""Name of the query-param pointing at project-id (tenant-id)"""


class Request(falcon.Request):
    """Variation of falcon.Request with context

    Following class enhances :py:class:`falcon.Request` with
    :py:class:`context.RequestContext`.

    """

    def __init__(self, env, options=None):
        super(Request, self).__init__(env, options)
        self.context = context.RequestContext.from_environ(self.env)

    @property
    def project_id(self):
        """Returns project-id (tenant-id)

        :return: project-id
        :rtype: str

        """
        return self.context.tenant

    @property
    def cross_project_id(self):
        """Returns project-id (tenant-id) found in query params.

        This particular project-id is later on identified as
        cross-project-id

        :return: project-id
        :rtype: str

        """
        return self.get_param(_TENANT_ID_PARAM, required=False)

    @property
    def user_id(self):
        """Returns user-id

        :return: user-id
        :rtype: str

        """
        return self.context.user

    @property
    def roles(self):
        """Returns roles associated with user

        :return: user's roles
        :rtype: list

        """
        return self.context.roles

    def get_param_as_datetime(self, param_name, store=None, required=False, default=None):
        param = self.get_param(param_name, required=required, default=default)
        result = iso8601.parse_date(param) if param is not None else None
        if store is not None:
            store[param_name] = result
        return result

    def get_param_as_dimensions(self, param_name, store=None, required=False):
        param = self.get_param_as_list(param_name, required=required)
        result = {}
        if param is not None:
            for dimension in param:
                dimension_name_value = dimension.split(':')
                if len(dimension_name_value) == 2:
                    result[dimension_name_value[0]] = dimension_name_value[1]
                elif len(dimension_name_value) == 1:
                    result[dimension_name_value[0]] = ""
                else:
                    err_msg = "Dimension {} is malformed".format(dimension)
                    raise exceptions.HTTPUnprocessableEntityError('Dimensions are malformed', err_msg)

        if store is not None:
            store[param_name] = result

        return result

    def get_param_as_list(self, param_name, transform=None, store=None, required=False, default=None):
        result = super(Request, self).get_param_as_list(param_name, transform=transform,
                                                        required=required, store=store)
        if result is None:
            result = default
        if store is not None:
            store[param_name] = result
        return result

    def get_param_as_int(self, param_name, store=None, required=False, min=None, max=None,
                         default=None):
        result = super(Request, self).get_param_as_int(param_name, required=required, min=min,
                                                       max=max, store=store)
        if result is None:
            result = default
        if store is not None:
            store[param_name] = result
        return result

    @property
    def limit(self):
        """Returns LIMIT query param value.

        'limit' is not required query param.
        In case it is not found, py:data:'.constants.PAGE_LIMIT'
        value is returned.

        :return: value of 'limit' query param or default value
        :rtype: int
        :raise exceptions.HTTPUnprocessableEntityError: if limit is not valid integer

        """
        limit = self.get_param_as_int('limit', required=False)
        if limit is not None:
            if limit > constants.PAGE_LIMIT:
                return constants.PAGE_LIMIT
            elif limit < 0:
                err_msg = 'Limit parameter must be a positive integer'
                raise exceptions.HTTPUnprocessableEntityError('Invalid limit', err_msg)
            else:
                return limit
        else:
            return constants.PAGE_LIMIT

    def __repr__(self):
        return '%s, context=%s' % (self.path, self.context)
