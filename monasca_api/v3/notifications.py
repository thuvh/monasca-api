# (C) Copyright 2014-2017 Hewlett Packard Enterprise Development LP
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
from oslo_log import log

from monasca_api.common.repositories import exceptions
from monasca_api.common import exceptions as http_exceptions
from monasca_api.v3.common import auth
from monasca_api.v3.common import pagination
from monasca_api.v3.common import utils
from monasca_api.v3.common import validation

LOG = log.getLogger(__name__)

DEFAULT_AUTHORIZED_ROLES = cfg.CONF.security.default_authorized_roles
GET_NOTIFICATION_AUTHORIZED_ROLES = (cfg.CONF.security.default_authorized_roles +
                                     cfg.CONF.security.read_only_authorized_roles)


class Notifications(object):
    def __init__(self):
        super(Notifications, self).__init__()

        self._region = cfg.CONF.region
        self._notifications_repo = simport.load(
            cfg.CONF.repositories.notifications_driver)()
        self._notification_method_type_repo = simport.load(
            cfg.CONF.repositories.notification_method_type_driver)()
        self.valid_periods = cfg.CONF.valid_notification_periods

    def _validate_notification_method_type_exist(self, nmt):
        notification_methods = self._notification_method_type_repo.list_notification_method_types()
        exists = nmt.upper() in notification_methods

        if not exists:
            LOG.warning("Found no notification method type  {} . Did you install/enable the plugin for that type?"
                        .format(nmt))
            raise falcon.HTTPBadRequest('Bad Request', "Not a valid notification method type {} ".format(nmt))

    def _validate_name_not_conflicting(self, tenant_id, name, expected_id=None):
        notification = self._notifications_repo.find_notification_by_name(tenant_id, name)

        if notification:
            if not expected_id:
                LOG.warning("Found existing notification method for {} with tenant_id {}".format(name, tenant_id))
                raise exceptions.AlreadyExistsException(
                    "A notification method with the name {} already exists".format(name))

            found_notification_id = notification['id']
            if found_notification_id != expected_id:
                LOG.warning("Found existing notification method for {} with tenant_id {} with unexpected id {}"
                            .format(name, tenant_id, found_notification_id))
                raise exceptions.AlreadyExistsException(
                    "A notification method with name {} already exists with id {}"
                    .format(name, found_notification_id))

    def _validate_notification(self, req, notification):
        """Validates the notification

        :param req: the original request
        :param notification: An event object.
        :raises falcon.HTTPBadRequest
        :raises monasca_api.common.repositories.exceptions.AlreadyExistsException
        """
        name = notification['name']
        if not isinstance(name, basestring):
            raise http_exceptions.HTTPUnprocessableEntityError(
                'Unproccessable Entity',
                'Invalid type for name: {} is not a string type'.format(name))
        if len(name) < 1 or len(name) > 255:
            raise http_exceptions.HTTPUnprocessableEntityError(
                'Unprocessable Entity'
                'Invalid length for name: {} is not between 1 and 255'.format(name))

        address = notification['address']
        if not isinstance(address, basestring):
            raise http_exceptions.HTTPUnprocessableEntityError(
                'Unprocessable Entity',
                'Invalid type for name: {} is not a string type'.format(address))
        if len(address) < 1 or len(address) > 255:
            raise http_exceptions.HTTPUnprocessableEntityError(
                'Unprocessable Entity',
                'Invalid length for name: {} is not between 1 and 255'.format(address))

        _type = notification['type']
        if not isinstance(_type, basestring):
            raise http_exceptions.HTTPUnprocessableEntityError(
                'Unprocessable Entity',
                'Invalid type for name: {} is not a string type'.format(_type))
        notification['type'] = _type.upper()

        try:
            period = int(notification['period'])
            assert period > 0
            notification['period'] = period
        except Exception:
            raise http_exceptions.HTTPUnprocessableEntityError(
                'Unprocessable Entity',
                'Period must be a positive integer')

        self._validate_notification_method_type_exist(notification['type'])
        self._validate_name_not_conflicting(req.tenant_id, notification['name'])

    def _build_notification_result(self, notification_row):

        result = {
            u'id': notification_row['id'],
            u'name': notification_row['name'],
            u'type': notification_row['type'],
            u'address': notification_row['address'],
            u'period': notification_row['period']
        }

        return result

    @utils.exception_translator
    @auth.Authorize(authorized_roles=DEFAULT_AUTHORIZED_ROLES)
    def on_post(self, req, res):
        notification = utils.parse_json_body(req,
                                             required_fields=['name', 'type', 'address'],
                                             defaults={'period': 0},
                                             validation=self._validate_notification)

        self._validate_notification(req.tenant_id, notification)

        notification_id = self._notifications_repo.create_notification(
            req.tenant_id,
            notification['name'],
            notification['type'],
            notification['address'],
            notification['period'])

        notification['id'] = notification_id
        pagination.add_links_to_resource(notification, req.uri)

        res.body = utils.dumps_json_utf8(notification)
        res.status = falcon.HTTP_201

    @utils.exception_translator
    @auth.Authorize(authorized_roles=GET_NOTIFICATION_AUTHORIZED_ROLES)
    def on_get(self, req, res, notification_method_id=None):
        if notification_method_id is None:
            sort_by = req.get_param_as_list('sort_by', default=[])
            offset = req.get_param_as_int('offset')
            limit = req.limit

            allowed_sort_by = {'id', 'name', 'type', 'address',
                               'updated_at', 'created_at'}
            validation.validate_sort_by(sort_by, allowed_sort_by)

            # TODO(Ryan) move this formatting to repo level
            rows = self._notifications_repo.list_notifications(req.tenant_id, sort_by,
                                                               offset, limit)

            results = [self._build_notification_result(row) for row in rows]
            pagination.add_links_to_resource_list(results, req.uri)
            paginated_results = pagination.paginate(results, req.uri, limit)

            res.body = utils.dumps_json_utf8(paginated_results)
            res.status = falcon.HTTP_200
        else:
            row = self._notifications_repo.list_notification(req.tenant_id,
                                                             notification_method_id)
            result = self._build_notification_result(row)

            req_uri_no_id = req.uri.replace('/' + notification_method_id, "")
            paginated_result = pagination.add_links_to_resource(result, req_uri_no_id)
            res.body = utils.dumps_json_utf8(paginated_result)
            res.status = falcon.HTTP_200

    @utils.exception_translator
    @auth.Authorize(authorized_roles=DEFAULT_AUTHORIZED_ROLES)
    def on_delete(self, req, res, notification_method_id):
        self._notifications_repo.delete_notification(req.tenant_id,
                                                     notification_method_id)
        res.status = falcon.HTTP_204

    @utils.exception_translator
    @auth.Authorize(authorized_roles=DEFAULT_AUTHORIZED_ROLES)
    def on_put(self, req, res, notification_method_id):
        # verify the notification id exists before validating anything else
        self._notifications_repo.list_notification(req.tenant_id, notification_method_id)

        notification = utils.parse_json_body(req,
                                             required_fields=['name', 'type', 'address', 'period'],
                                             validation=self._validate_notification)

        self._validate_notification(req.tenant_id, notification)

        self._notifications_repo.update_notification(notification_method_id,
                                                     req.tenant_id,
                                                     notification['name'],
                                                     notification['type'],
                                                     notification['address'],
                                                     notification['period'])

        notification['id'] = notification_method_id
        pagination.add_links_to_resource(notification, req.uri)

        res.body = utils.dumps_json_utf8(notification)
        res.status = falcon.HTTP_200

    @utils.exception_translator
    @auth.Authorize(authorized_roles=DEFAULT_AUTHORIZED_ROLES)
    def on_patch(self, req, res, notification_method_id):
        # verify notification id exists before validating further
        old_notification = self._notifications_repo.list_notification(req.tenant_id,
                                                                      notification_method_id)
        notification = utils.parse_json_body(req,
                                             defaults={'name': old_notification['name'],
                                                       'type': old_notification['type'],
                                                       'address': old_notification['address'],
                                                       'period': old_notification['period']},
                                             validation=self._validate_notification)

        self._validate_notification(req.tenant_id, notification)

        self._notifications_repo.update_notification(notification_method_id,
                                                     req.tenant_id,
                                                     notification['name'],
                                                     notification['notification_type'],
                                                     notification['address'],
                                                     notification['period'])

        notification['id'] = notification_method_id
        pagination.add_links_to_resource(notification, req.uri)

        res.body = utils.dumps_json_utf8(notification)
        res.status = falcon.HTTP_200
