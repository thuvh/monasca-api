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

from monasca_api.api import alarm_group_definitions_api_v2
from monasca_api.common.repositories import exceptions
from monasca_api.v2.common.exceptions import HTTPUnprocessableEntityError
from monasca_api.v2.common.schemas import (
    alarm_group_definition_request_body_schema as schema_group_definition)
from monasca_api.v2.reference import alarming
from monasca_api.v2.reference import helpers
from monasca_api.v2.reference import resource

LOG = log.getLogger(__name__)


class AlarmGroupDefinitions(alarm_group_definitions_api_v2.
                            AlarmGroupDefinitionsV2API, alarming.Alarming):

    def __init__(self):
        try:
            super(AlarmGroupDefinitions, self).__init__()
            self._region = cfg.CONF.region
            self._default_authorized_roles = (
                cfg.CONF.security.default_authorized_roles)
            self._get_alarm_group_definitions_authorized_roles = (
                cfg.CONF.security.default_authorized_roles +
                cfg.CONF.security.read_only_authorized_roles)
            self._alarm_group_definitions_repo = simport.load(
                cfg.CONF.repositories.alarm_group_definitions_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    @resource.resource_try_catch_block
    def on_post(self, req, res):
        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_group_definition = helpers.read_json_msg_body(req)

        self._validate_alarm_group_definition(alarm_group_definition)

        name = get_query_alarm_group_definition_param(alarm_group_definition,
                                                      "name")
        matchers = get_query_alarm_group_definition_param(
            alarm_group_definition, "matchers")
        group_wait = get_query_alarm_group_definition_group_wait(
            alarm_group_definition)
        repeat_interval = get_query_alarm_group_definition_repeat_interval(
            alarm_group_definition)
        exclusions = get_query_alarm_group_definition_exclusions(
            alarm_group_definition)
        alarm_actions = get_query_alarm_group_definition_actions(
            alarm_group_definition, "alarm_actions")
        ok_actions = get_query_alarm_group_definition_actions(
            alarm_group_definition, "ok_actions")
        undetermined_actions = get_query_alarm_group_definition_actions(
            alarm_group_definition, "undetermined_actions")

        result = self._alarm_group_definition_create(req.project_id,
                                                     name,
                                                     matchers,
                                                     group_wait,
                                                     repeat_interval,
                                                     exclusions,
                                                     alarm_actions,
                                                     ok_actions,
                                                     undetermined_actions)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_201

    @resource.resource_try_catch_block
    def on_get(self, req, res, alarm_group_definition_id=None):
        helpers.validate_authorization(
            req, self._get_alarm_group_definitions_authorized_roles)

        if alarm_group_definition_id is None:
            name = helpers.get_query_name(req)
            offset = helpers.get_query_param(req, 'offset')
            if offset is not None and not isinstance(offset, int):
                try:
                    offset = int(offset)
                except Exception:
                    raise HTTPUnprocessableEntityError(
                        'Unprocessable Entity, Offset value {} must be an '
                        'integer'.format(offset))

            result = self._alarm_group_definition_list(
                req.project_id, name, req.uri, offset, req.limit)

            res.body = helpers.dumpit_utf8(result)
            res.status = falcon.HTTP_200

        else:
            helpers.validate_authorization(
                req, self._get_alarm_group_definitions_authorized_roles)

            result = self._alarm_group_definition_show(
                req.project_id, alarm_group_definition_id)

            helpers.add_links_to_resource(
                result, re.sub('/' + alarm_group_definition_id, '', req.uri))
            res.body = helpers.dumpit_utf8(result)
            res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_put(self, req, res, alarm_group_definition_id):

        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_group_definition = helpers.read_json_msg_body(req)

        self._validate_alarm_group_definition(alarm_group_definition,
                                              require_all=True)

        name = get_query_alarm_group_definition_param(
            alarm_group_definition, "name")
        matchers = get_query_alarm_group_definition_param(
            alarm_group_definition, "matchers")
        group_wait = get_query_alarm_group_definition_group_wait(
            alarm_group_definition)
        repeat_interval = get_query_alarm_group_definition_repeat_interval(
            alarm_group_definition)
        exclusions = get_query_alarm_group_definition_exclusions(
            alarm_group_definition)
        alarm_actions = get_query_alarm_group_definition_actions(
            alarm_group_definition, "alarm_actions")
        ok_actions = get_query_alarm_group_definition_actions(
            alarm_group_definition, "ok_actions")
        undetermined_actions = get_query_alarm_group_definition_actions(
            alarm_group_definition, "undetermined_actions")

        result = self._alarm_group_definition_update_or_patch(
            req.project_id, alarm_group_definition_id, name, matchers,
            group_wait, repeat_interval, exclusions, alarm_actions, ok_actions,
            undetermined_actions, patch=False)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_patch(self, req, res, alarm_group_definition_id):

        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_group_definition = helpers.read_json_msg_body(req)

        # Optional args
        name = get_query_alarm_group_definition_param(alarm_group_definition,
                                                      "name", return_none=True)
        matchers = get_query_alarm_group_definition_param(
            alarm_group_definition, "matchers", return_none=True)
        group_wait = get_query_alarm_group_definition_group_wait(
            alarm_group_definition, return_none=True)
        repeat_interval = get_query_alarm_group_definition_repeat_interval(
            alarm_group_definition, return_none=True)
        alarm_actions = get_query_alarm_group_definition_actions(
            alarm_group_definition, "alarm_actions", return_none=True)
        ok_actions = get_query_alarm_group_definition_actions(
            alarm_group_definition, "ok_actions", return_none=True)
        undetermined_actions = get_query_alarm_group_definition_actions(
            alarm_group_definition, "undetermined_actions", return_none=True)
        exclusions = get_query_alarm_group_definition_exclusions(
            alarm_group_definition, return_none=True)

        result = self._alarm_group_definition_update_or_patch(
            req.project_id, alarm_group_definition_id, name,
            matchers, group_wait, repeat_interval, exclusions, alarm_actions,
            ok_actions, undetermined_actions, patch=True)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_delete(self, req, res, alarm_group_definition_id):

        helpers.validate_authorization(req, self._default_authorized_roles)
        self._alarm_group_definition_delete(req.project_id,
                                            alarm_group_definition_id)
        res.status = falcon.HTTP_204

    def _alarm_group_definition_delete(self, tenant_id,
                                       alarm_group_definition_id):
        if not self._alarm_group_definitions_repo\
                .delete_alarm_group_definition(tenant_id,
                                               alarm_group_definition_id):
            raise falcon.HTTPNotFound

        self._send_alarm_group_definition_deleted_event(
            alarm_group_definition_id)

    def _send_alarm_group_definition_deleted_event(self,
                                                   alarm_group_definition_id):
        alarm_group_definition_deleted_event_msg = {
            u"alarm-group-definition-deleted": {u"id":
                                                alarm_group_definition_id}}
        self.send_event(self.events_message_queue,
                        alarm_group_definition_deleted_event_msg)

    def _alarm_group_definition_update_or_patch(
            self, tenant_id, alarm_group_definition_id, name, matchers,
            group_wait, repeat_interval, exclusions, alarm_actions, ok_actions,
            undetermined_actions, patch):
        if name:
            self._validate_name_not_conflicting(
                tenant_id, name, expected_id=alarm_group_definition_id)

        alarm_group_definition_row = (
            self._alarm_group_definitions_repo.
            update_or_patch_alarm_group_definition(
                tenant_id,
                alarm_group_definition_id,
                name,
                matchers,
                group_wait,
                repeat_interval,
                exclusions,
                alarm_actions,
                ok_actions,
                undetermined_actions,
                patch))

        result = self._build_alarm_group_definition_show_result(
            alarm_group_definition_row)
        # Not all of the passed in parameters will be set if this called
        # from on_patch vs on_update. The alarm-group-definition-updated event
        # MUST have all of the fields set so use the dict built from the
        # data returned from the database
        alarm_group_definition_event_dict = (
            {u'tenantId': tenant_id,
             u'id': alarm_group_definition_id,
             u'name': result['name'],
             u'matchers': result['matchers'],
             u'group_wait': result['group_wait'],
             u'repeat_interval': result['repeat_interval'],
             u'exclusions': exclusions,
             u'alarm_actions': alarm_actions,
             u'ok_actions': ok_actions,
             u'undetermined_actions': undetermined_actions})

        alarm_group_definition_updated_event = (
            {u'alarm-group-definition-updated':
             alarm_group_definition_event_dict})

        self.send_event(self.events_message_queue,
                        alarm_group_definition_updated_event)

        return result

    def _validate_alarm_group_definition(self, alarm_group_definition,
                                         require_all=False):
        try:
            schema_group_definition.validate(alarm_group_definition,
                                             require_all=require_all)
        except Exception as ex:
            LOG.debug(ex)
            raise HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))

    @resource.resource_try_catch_block
    def _alarm_group_definition_create(self, tenant_id, name, matchers,
                                       group_wait, repeat_interval,
                                       exclusions, alarm_actions, ok_actions,
                                       undetermined_actions):
        self._validate_name_not_conflicting(tenant_id, name)
        alarm_group_definition_id = (
            self._alarm_group_definitions_repo
                .create_alarm_group_definition(tenant_id, name, matchers,
                                               group_wait, repeat_interval,
                                               exclusions, alarm_actions,
                                               ok_actions,
                                               undetermined_actions))

        self._send_alarm_group_definition_created_event(
            tenant_id, alarm_group_definition_id, name, matchers,
            group_wait, repeat_interval, exclusions, alarm_actions,
            ok_actions, undetermined_actions)

        result = (
            {u'alarm_actions': alarm_actions,
             u'ok_actions': ok_actions,
             u'undetermined_actions': undetermined_actions,
             u'repeat_interval': repeat_interval,
             u'group_wait': group_wait,
             u'exclusions': exclusions,
             u'matchers': matchers,
             u'id': alarm_group_definition_id,
             u'name': name})

        return result

    def _alarm_group_definition_show(self, tenant_id, group_definition_id):

        alarm_group_definition_row = (
            self._alarm_group_definitions_repo.get_alarm_group_definition(
                tenant_id, group_definition_id))

        return self._build_alarm_group_definition_show_result(
            alarm_group_definition_row)

    def _build_alarm_group_definition_show_result(
            self, alarm_group_definition_row):

        matchers = get_comma_separated_str_as_list(alarm_group_definition_row['matchers'])

        alarm_actions_list = get_comma_separated_str_as_list(
            alarm_group_definition_row['alarm_actions'])

        ok_actions_list = get_comma_separated_str_as_list(
            alarm_group_definition_row['ok_actions'])

        undetermined_actions_list = get_comma_separated_str_as_list(
            alarm_group_definition_row['undetermined_actions'])

        exclusions = (alarm_group_definition_row['exclusions']
                      if alarm_group_definition_row['exclusions'] is not None
                      else None)
        group_wait = (alarm_group_definition_row['group_wait']
                      if alarm_group_definition_row['group_wait'] is not None
                      else '30s')
        repeat_interval = (alarm_group_definition_row['repeat_interval']
                           if alarm_group_definition_row['repeat_interval'] is not None
                           else '2h')

        result = {
            u'alarm_actions': alarm_actions_list,
            u'undetermined_actions': undetermined_actions_list,
            u'ok_actions': ok_actions_list,
            u'matchers': matchers,
            u'exclusions': exclusions,
            u'id': alarm_group_definition_row['id'].decode('utf8'),
            u'name': alarm_group_definition_row['name'].decode('utf8'),
            u'group_wait': group_wait,
            u'repeat_interval': repeat_interval}

        return result

    def _alarm_group_definition_list(self, tenant_id, name, req_uri, offset,
                                     limit):
        alarm_group_definition_rows = (
            self._alarm_group_definitions_repo.get_alarm_group_definitions(
                tenant_id, name, offset, limit))
        result = []
        for alarm_group_definition_row in alarm_group_definition_rows:
            matchers = get_comma_separated_str_as_list(
                alarm_group_definition_row['matchers'])

            alarm_actions_list = get_comma_separated_str_as_list(
                alarm_group_definition_row['alarm_actions'])

            ok_actions_list = get_comma_separated_str_as_list(
                alarm_group_definition_row['ok_actions'])

            undetermined_actions_list = get_comma_separated_str_as_list(
                alarm_group_definition_row['undetermined_actions'])

            exclusions = alarm_group_definition_row['exclusions']

            agd = {u'id': alarm_group_definition_row['id'],
                   u'name': alarm_group_definition_row['name'],
                   u'matchers': matchers,
                   u'group_wait': alarm_group_definition_row['group_wait']
                   if (alarm_group_definition_row['group_wait']) else u'30s',
                   u'repeat_interval': alarm_group_definition_row['repeat_interval']
                   if (alarm_group_definition_row['repeat_interval']) else u'2h',
                   u'alarm_actions': alarm_actions_list,
                   u'ok_actions': ok_actions_list,
                   u'undetermined_actions': undetermined_actions_list,
                   u'exclusions': exclusions}

            helpers.add_links_to_resource(agd, req_uri)
            result.append(agd)
        return result

    def _validate_name_not_conflicting(self, tenant_id, name,
                                       expected_id=None):
        alarm_group_definitions = self._alarm_group_definitions_repo.\
            get_alarm_group_definitions(tenant_id=tenant_id, name=name,
                                        offset=None, limit=0)
        if alarm_group_definitions:
            if not expected_id:
                LOG.warning("Found existing alarm group definition for {} "
                            "with tenant_id {}".format(name, tenant_id))
                raise exceptions.AlreadyExistsException(
                    "An alarm group definition with the name {} already exists"
                    .format(name))

            found_group_definition_id = alarm_group_definitions[0]['id']
            if found_group_definition_id != expected_id:
                LOG.warning("Found existing alarm group definition for {} "
                            "with tenant_id {} with unexpected id {}".
                            format(name, tenant_id, found_group_definition_id))
                raise exceptions.AlreadyExistsException(
                    "An alarm group definition with the name {} already "
                    "exists with id {}".format(name,
                                               found_group_definition_id))

    def _send_alarm_group_definition_created_event(
            self, tenant_id, alarm_group_definition_id, name, matchers,
            group_wait, repeat_interval, exclusions, alarm_actions,
            ok_actions, undetermined_actions):
        alarm_group_definition_created_event_msg = {
            u'alarm-group-definition-created':
                {u'tenantId': tenant_id,
                 u'id': alarm_group_definition_id,
                 u'name': name,
                 u'matchers': matchers,
                 u'group_wait': group_wait,
                 u'repeat_interval': repeat_interval,
                 u'exclusions': exclusions,
                 u'alarm_actions': alarm_actions,
                 u'ok_actions': ok_actions,
                 u'undetermined_actions': undetermined_actions
                 }
        }
        self.send_event(self.events_message_queue,
                        alarm_group_definition_created_event_msg)


def get_query_alarm_group_definition_param(alarm_group_definition, param,
                                           return_none=False):
    try:
        if param in alarm_group_definition:
            param_value = alarm_group_definition[param]
            return param_value
        else:
            if return_none:
                return None
            else:
                raise Exception("Missing alarm grouping definition {}".format(
                    param))
    except Exception as ex:
        LOG.debug(ex)
        raise HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))


def get_query_alarm_group_definition_group_wait(alarm_group_definition,
                                                return_none=False):
    if 'group_wait' in alarm_group_definition:
        group_wait = alarm_group_definition['group_wait']
        return group_wait
    else:
        if return_none:
            return None
        else:
            return '30s'  # default to 30 seconds


def get_query_alarm_group_definition_repeat_interval(alarm_group_definition,
                                                     return_none=False):
    if 'repeat_interval' in alarm_group_definition:
        repeat_interval = alarm_group_definition['repeat_interval']
        return repeat_interval
    else:
        if return_none:
            return None
        else:
            return '2h'  # default to 2h


def get_query_alarm_group_definition_exclusions(alarm_group_definition,
                                                return_none=False):
    if 'exclusions' in alarm_group_definition:
        exclusions = alarm_group_definition['exclusions']
        return exclusions
    else:
        if return_none:
            return None
        else:
            return []


def get_query_alarm_group_definition_actions(
        alarm_group_definition, action_state, return_none=False):
    if action_state in alarm_group_definition:
        actions = alarm_group_definition[action_state]
        return actions
    else:
        if return_none:
            return None
        else:
            return []


def get_comma_separated_str_as_list(comma_separated_str):
    if not comma_separated_str:
        return []
    else:
        return comma_separated_str.decode('utf8').split(',')
