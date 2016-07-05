# (C) Copyright 2014-2016 Hewlett Packard Enterprise Development Company LP
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
from oslo_config import cfg
from oslo_log import log

from monasca_api.api import notificationstype_api_v2

LOG = log.getLogger(__name__)


class NotificationsType(notificationstype_api_v2.NotificationsTypeV2API):
    def __init__(self):
        super(NotificationsType, self).__init__()


    def _list_notifications(self):

        valid_notification_method_types = [types.upper() for types in cfg.CONF.valid_notification_method_types]
        return valid_notification_method_types

    def on_get(self, req, res):

        result = self._list_notifications()
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_200
