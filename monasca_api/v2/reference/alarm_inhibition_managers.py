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
import re

from monasca_common.simport import simport
from oslo_config import cfg
from oslo_log import log

from monasca_api.api import alarm_inhibition_managers_api_v2
from monasca_api.common.repositories import exceptions
from monasca_api.v2.common.exceptions import HTTPUnprocessableEntityError
from monasca_api.v2.common.schemas import (
    alarm_inhibition_manager_request_body_schema as schema_inhibition_manager)
from monasca_api.v2.reference import alarming
from monasca_api.v2.reference import helpers
from monasca_api.v2.reference import resource

LOG = log.getLogger(__name__)


class AlarmInhibitionManagers(alarm_inhibition_managers_api_v2.
                              AlarmInhibitionManagersV2API, alarming.Alarming):

    def __init__(self):
        try:
            super(AlarmInhibitionManagers, self).__init__()
            self._region = cfg.CONF.region
            self._default_authorized_roles = (
                cfg.CONF.security.default_authorized_roles)
            self._get_alarm_inhibition_managers_authorized_roles = (
                cfg.CONF.security.default_authorized_roles +
                cfg.CONF.security.read_only_authorized_roles)
            self._alarm_inhibition_managers_repo = simport.load(
                cfg.CONF.repositories.alarm_inhibition_managers_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    @resource.resource_try_catch_block
    def on_post(self, req, res):
        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_inhibition_manager = helpers.read_json_msg_body(req)
        self._validate_alarm_inhibition_manager(alarm_inhibition_manager)

        name = get_query_alarm_inhibition_manager_name(
            alarm_inhibition_manager)
        equal = get_query_alarm_inhibition_manager_equal(
            alarm_inhibition_manager)
        source_match = get_query_alarm_inhibition_manager_source_match(
            alarm_inhibition_manager)
        target_match = get_query_alarm_inhibition_manager_target_match(
            alarm_inhibition_manager)

        result = self._alarm_inhibition_manager_create(req.project_id, name,
                                                       equal, source_match,
                                                       target_match)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_201

    @resource.resource_try_catch_block
    def on_get(self, req, res, alarm_inhibition_manager_id=None):
        if alarm_inhibition_manager_id is None:
            helpers.validate_authorization(
                req, self._get_alarm_inhibition_managers_authorized_roles)

            name = helpers.get_query_name(req)
            offset = helpers.get_query_param(req, 'offset')
            if offset is not None and not isinstance(offset, int):
                try:
                    offset = int(offset)
                except Exception:
                    raise HTTPUnprocessableEntityError(
                        'Unprocessable Entity, Offset value {} must be an '
                        'integer'.format(offset))

            result = self._alarm_inhibition_manager_list(
                req.project_id, name, req.uri, offset, req.limit)

            res.body = helpers.dumpit_utf8(result)
            res.status = falcon.HTTP_200

        else:
            helpers.validate_authorization(
                req, self._get_alarm_inhibition_managers_authorized_roles)

            result = self._alarm_inhibition_manager_show(
                req.project_id, alarm_inhibition_manager_id)

            helpers.add_links_to_resource(
                result, re.sub('/' + alarm_inhibition_manager_id, '', req.uri))
            res.body = helpers.dumpit_utf8(result)
            res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_put(self, req, res, alarm_inhibition_manager_id):

        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_inhibition_manager = helpers.read_json_msg_body(req)

        self._validate_alarm_inhibition_manager(alarm_inhibition_manager,
                                                require_all=True)

        name = get_query_alarm_inhibition_manager_name(
            alarm_inhibition_manager)
        equal = get_query_alarm_inhibition_manager_equal(
            alarm_inhibition_manager)
        source_match = get_query_alarm_inhibition_manager_source_match(
            alarm_inhibition_manager)
        target_match = get_query_alarm_inhibition_manager_target_match(
            alarm_inhibition_manager)

        result = self._alarm_inhibition_manager_update_or_patch(
            req.project_id, alarm_inhibition_manager_id, name, equal,
            source_match, target_match, patch=False)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_patch(self, req, res, alarm_inhibition_manager_id):

        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_inhibition_manager = helpers.read_json_msg_body(req)

        # Optional args
        name = get_query_alarm_inhibition_manager_name(
            alarm_inhibition_manager, return_none=True)
        equal = get_query_alarm_inhibition_manager_equal(
            alarm_inhibition_manager, return_none=True)
        source_match = get_query_alarm_inhibition_manager_source_match(
            alarm_inhibition_manager, return_none=True)
        target_match = get_query_alarm_inhibition_manager_target_match(
            alarm_inhibition_manager, return_none=True)

        result = self._alarm_inhibition_manager_update_or_patch(
            req.project_id, alarm_inhibition_manager_id, name, equal,
            source_match, target_match, patch=True)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_delete(self, req, res, alarm_inhibition_manager_id):

        helpers.validate_authorization(req, self._default_authorized_roles)
        self._alarm_inhibition_manager_delete(req.project_id,
                                              alarm_inhibition_manager_id)
        res.status = falcon.HTTP_204

    def _alarm_inhibition_manager_delete(self, tenant_id,
                                         alarm_inhibition_manager_id):
        if not self._alarm_inhibition_managers_repo\
                .delete_alarm_inhibition_manager(tenant_id,
                                                 alarm_inhibition_manager_id):
            raise falcon.HTTPNotFound

        self._send_alarm_inhibition_manager_deleted_event(
            alarm_inhibition_manager_id)

    def _send_alarm_inhibition_manager_deleted_event(
            self, alarm_inhibition_manager_id):
        alarm_inhibition_manager_deleted_event_msg = {
            u"alarm-inhibition-manager-deleted": {u"id":
                                                  alarm_inhibition_manager_id}}
        self.send_event(self.events_message_queue,
                        alarm_inhibition_manager_deleted_event_msg)

    def _alarm_inhibition_manager_update_or_patch(
            self, tenant_id, alarm_inhibition_manager_id, name, equal,
            source_match, target_match, patch):
        if name:
            self._validate_name_not_conflicting(
                tenant_id, name, expected_id=alarm_inhibition_manager_id)

        alarm_inhibition_manager_row = (
            self._alarm_inhibition_managers_repo.
            update_or_patch_alarm_inhibition_manager(
                tenant_id,
                alarm_inhibition_manager_id,
                name,
                equal,
                source_match,
                target_match,
                patch))

        result = self._build_alarm_inhibition_manager_show_result(
            alarm_inhibition_manager_row)
        # Not all of the passed in parameters will be set if this called
        # from on_patch vs on_update. The alarm-inhibition-manager-updated
        # event MUST have all of the fields set so use the dict built from the
        # data returned from the database
        alarm_inhibition_manager_event_dict = (
            {u'tenantId': tenant_id,
             u'id': alarm_inhibition_manager_id,
             u'name': result['name'],
             u'equal': result['equal'],
             u'source_match': result['source_match'],
             u'target_match': result['target_match']})

        alarm_inhibition_manager_updated_event = (
            {u'alarm-inhibition-manager-updated':
             alarm_inhibition_manager_event_dict})

        self.send_event(self.events_message_queue,
                        alarm_inhibition_manager_updated_event)

        return result

    def _validate_alarm_inhibition_manager(self, alarm_inhibition_manager,
                                           require_all=False):
        try:
            schema_inhibition_manager.validate(alarm_inhibition_manager,
                                               require_all=require_all)
        except Exception as ex:
            LOG.debug(ex)
            raise HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))

    @resource.resource_try_catch_block
    def _alarm_inhibition_manager_create(self, tenant_id, name, equal,
                                         source_match, target_match):
        self._validate_name_not_conflicting(tenant_id, name)
        alarm_inhibition_manager_id = (
            self._alarm_inhibition_managers_repo
                .create_alarm_inhibition_manager(tenant_id, name, equal,
                                                 source_match, target_match))

        self._send_alarm_inhibition_manager_created_event(
            tenant_id, alarm_inhibition_manager_id, name, equal,
            source_match, target_match)

        result = (
            {u'id': alarm_inhibition_manager_id,
             u'name': name,
             u'equal': equal,
             u'source_match': source_match,
             u'target_match': target_match
             })

        return result

    def _alarm_inhibition_manager_show(self, tenant_id, inhibition_manager_id):

        alarm_inhibition_manager_row = (
            self._alarm_inhibition_managers_repo.get_alarm_inhibition_manager(
                tenant_id, inhibition_manager_id))

        return self._build_alarm_inhibition_manager_show_result(
            alarm_inhibition_manager_row)

    def _build_alarm_inhibition_manager_show_result(
            self, alarm_inhibition_manager_row):

        equal = get_comma_separated_str_as_list(alarm_inhibition_manager_row[
                                                'equal'])
        source_match = get_comma_separated_str_as_list(
            alarm_inhibition_manager_row['source_match'])
        target_match = get_comma_separated_str_as_list(
            alarm_inhibition_manager_row['target_match'])

        result = {
            u'id': alarm_inhibition_manager_row['id'].decode('utf8'),
            u'name': alarm_inhibition_manager_row['name'].decode('utf8'),
            u'equal': equal,
            u'source_match': source_match,
            u'target_match': target_match}

        return result

    def _alarm_inhibition_manager_list(self, tenant_id, name, req_uri, offset,
                                       limit):
        alarm_inhibition_manager_rows = (
            self._alarm_inhibition_managers_repo.get_alarm_inhibition_managers(
                tenant_id, name, offset, limit))
        result = []
        for alarm_inhibition_manager_row in alarm_inhibition_manager_rows:
            equal = get_comma_separated_str_as_list(
                alarm_inhibition_manager_row['equal'])
            source_match = get_comma_separated_str_as_list(
                alarm_inhibition_manager_row['source_match'])
            target_match = get_comma_separated_str_as_list(
                alarm_inhibition_manager_row['target_match'])

            aim = {u'id': alarm_inhibition_manager_row['id'],
                   u'name': alarm_inhibition_manager_row['name'],
                   u'equal': equal,
                   u'source_match': source_match,
                   u'target_match': target_match}

            helpers.add_links_to_resource(aim, req_uri)
            result.append(aim)
        return result

    def _validate_name_not_conflicting(self, tenant_id, name,
                                       expected_id=None):
        alarm_inhibition_managers = self._alarm_inhibition_managers_repo.\
            get_alarm_inhibition_managers(tenant_id=tenant_id, name=name,
                                          offset=None, limit=0)
        if alarm_inhibition_managers:
            if not expected_id:
                LOG.warning("Found existing alarm inhibition manager for {} "
                            "with tenant_id {}".format(name, tenant_id))
                raise exceptions.AlreadyExistsException(
                    "An alarm inhibition manager with the name {} already "
                    "exists"
                    .format(name))

            found_inhibition_manager_id = alarm_inhibition_managers[0]['id']
            if found_inhibition_manager_id != expected_id:
                LOG.warning("Found existing alarm inhibition manager for {} "
                            "with tenant_id {} with unexpected id {}".
                            format(name, tenant_id, found_inhibition_manager_id))
                raise exceptions.AlreadyExistsException(
                    "An alarm inhibition manager with the name {} already "
                    "exists with id {}".format(name,
                                               found_inhibition_manager_id))

    def _send_alarm_inhibition_manager_created_event(
            self, tenant_id, alarm_inhibition_manager_id, name, equal,
            source_match, target_match):
        alarm_inhibition_manager_created_event_msg = {
            u'alarm-inhibition-manager-created':
                {u'tenantId': tenant_id,
                 u'id': alarm_inhibition_manager_id,
                 u'name': name,
                 u'equal': equal,
                 u'source_match': source_match,
                 u'target_match': target_match
                 }
        }
        self.send_event(self.events_message_queue,
                        alarm_inhibition_manager_created_event_msg)


def get_query_alarm_inhibition_manager_name(alarm_inhibition_manager,
                                            return_none=False):
    try:
        if 'name' in alarm_inhibition_manager:
            name = alarm_inhibition_manager['name']
            return name
        else:
            if return_none:
                return None
            else:
                raise Exception("Missing inhibition name")
    except Exception as ex:
        LOG.debug(ex)
        raise HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))


def get_query_alarm_inhibition_manager_equal(alarm_inhibition_manager,
                                             return_none=False):
    try:
        if 'equal' in alarm_inhibition_manager:
            equal = alarm_inhibition_manager['equal']
            return equal
        else:
            if return_none:
                return None
            else:
                raise Exception("Missing inhibition equal field")
    except Exception as ex:
        LOG.debug(ex)
        raise HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))


def get_query_alarm_inhibition_manager_source_match(alarm_inhibition_manager,
                                                    return_none=False):
    try:
        if 'source_match' in alarm_inhibition_manager:
            source_match = alarm_inhibition_manager['source_match']
            return source_match
        else:
            if return_none:
                return None
            else:
                raise Exception("Missing inhibition source match field")
    except Exception as ex:
        LOG.debug(ex)
        raise HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))


def get_query_alarm_inhibition_manager_target_match(alarm_inhibition_manager,
                                                    return_none=False):
    try:
        if 'target_match' in alarm_inhibition_manager:
            target_match = alarm_inhibition_manager['target_match']
            return target_match
        else:
            if return_none:
                return None
            else:
                raise Exception("Missing inhibition target match field")
    except Exception as ex:
        LOG.debug(ex)
        raise HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))


def get_comma_separated_str_as_list(comma_separated_str):
    if not comma_separated_str:
        return []
    else:
        return comma_separated_str.decode('utf8').split(',')
