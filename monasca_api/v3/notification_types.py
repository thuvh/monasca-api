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


DEFAULT_AUTHORIZED_ROLES = cfg.CONF.security.default_authorized_roles


class NotificationsType(object):
    def __init__(self):
        super(NotificationsType, self).__init__()
        self._notification_method_type_repo = simport.load(
            cfg.CONF.repositories.notification_method_type_driver)()

    def _list_notifications(self, uri, limit):
        rows = self._notification_method_type_repo.list_notification_method_types()
        result = [dict(type=row) for row in rows]
        return pagination.paginate(result, uri, limit)

    @utils.exception_translator
    @auth.Authorize(authorized_roles=DEFAULT_AUTHORIZED_ROLES)
    def on_get(self, req, res):

        # This is to provide consistency. Pagination is not really supported here as there
        # are not that many rows
        result = self._list_notifications(req.uri, req.limit)

        res.body = utils.dumps_json_utf8(result)
        res.status = falcon.HTTP_200
