# (C) Copyright 2016-2017 Hewlett Packard Enterprise Development LP
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
from monasca_common.simport import simport
from oslo_config import cfg

from monasca_api.v3.common import auth
from monasca_api.v3.common import pagination
from monasca_api.v3.common import utils

GET_NOTIFICATION_AUTHORIZED_ROLES = (cfg.CONF.security.default_authorized_roles +
                                     cfg.CONF.security.read_only_authorized_roles)


class NotificationTypes(object):
    def __init__(self):
        super(NotificationTypes, self).__init__()
        self._notification_method_type_repo = simport.load(
            cfg.CONF.repositories.notification_method_type_driver)()

    @utils.exception_translator
    @auth.Authorize(authorized_roles=GET_NOTIFICATION_AUTHORIZED_ROLES)
    def on_get(self, req, res):
        # This is to provide consistency. Pagination is not really supported here as there
        # are not that many rows
        rows = self._notification_method_type_repo.list_notification_method_types()
        result = [dict(type=row) for row in rows]

        paginated_result = pagination.paginate(result, req.uri, req.limit)

        res.body = utils.dumps_json_utf8(paginated_result)
        res.status = falcon.HTTP_200
