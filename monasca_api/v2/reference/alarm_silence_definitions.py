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
# under the License.'

import datetime
import falcon
import re

from monasca_common.simport import simport
from oslo_config import cfg
from oslo_log import log

from monasca_api.api import alarm_silence_definitions_api_v2
from monasca_api.common.repositories import exceptions
from monasca_api.v2.common.exceptions import HTTPUnprocessableEntityError
from monasca_api.v2.common.schemas import (
    alarm_silence_definition_request_body_schema as schema_silence_definition)
from monasca_api.v2.reference import alarming
from monasca_api.v2.reference import helpers
from monasca_api.v2.reference import resource

LOG = log.getLogger(__name__)


class AlarmSilenceDefinitions(alarm_silence_definitions_api_v2.
                              AlarmSilenceDefinitionsV2API, alarming.Alarming):

    def __init__(self):
        try:
            super(AlarmSilenceDefinitions, self).__init__()
            self._region = cfg.CONF.region
            self._default_authorized_roles = (
                cfg.CONF.security.default_authorized_roles)
            self._get_alarm_silence_definitions_authorized_roles = (
                cfg.CONF.security.default_authorized_roles +
                cfg.CONF.security.read_only_authorized_roles)
            self._alarm_silence_definitions_repo = simport.load(
                cfg.CONF.repositories.alarm_silence_definitions_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    @resource.resource_try_catch_block
    def on_post(self, req, res):
        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_silence_definition = helpers.read_json_msg_body(req)

        self._validate_alarm_silence_definition(alarm_silence_definition)

        name = get_query_alarm_silence_definition_param(
            alarm_silence_definition, "name")
        description = get_query_alarm_silence_definition_description(
            alarm_silence_definition)
        matchers = get_query_alarm_silence_definition_param(
            alarm_silence_definition, "matchers")
        start_time = get_query_alarm_silence_definition_start_time(
            alarm_silence_definition)
        silence_duration = get_query_alarm_silence_definition_silence_duration(
            alarm_silence_definition)

        result = self._alarm_silence_definition_create(req.project_id,
                                                       name,
                                                       description,
                                                       matchers,
                                                       start_time,
                                                       silence_duration)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_201

    @resource.resource_try_catch_block
    def on_get(self, req, res, alarm_silence_definition_id=None):
        helpers.validate_authorization(
            req, self._get_alarm_silence_definitions_authorized_roles)
        if alarm_silence_definition_id is None:
            name = helpers.get_query_name(req)
            offset = helpers.get_query_param(req, 'offset')
            if offset is not None and not isinstance(offset, int):
                try:
                    offset = int(offset)
                except Exception:
                    raise HTTPUnprocessableEntityError(
                        'Unprocessable Entity, Offset value {} must be an '
                        'integer'.format(offset))

            result = self._alarm_silence_definition_list(
                req.project_id, name, req.uri, offset, req.limit)
            LOG.error('~~~~~~~~~~result: {}'.format(result))

            res.body = helpers.dumpit_utf8(result)
            res.status = falcon.HTTP_200

        else:
            helpers.validate_authorization(
                req, self._get_alarm_silence_definitions_authorized_roles)

            result = self._alarm_silence_definition_show(
                req.project_id, alarm_silence_definition_id)

            helpers.add_links_to_resource(
                result, re.sub('/' + alarm_silence_definition_id, '', req.uri))
            res.body = helpers.dumpit_utf8(result)
            res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_put(self, req, res, alarm_silence_definition_id):

        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_silence_definition = helpers.read_json_msg_body(req)

        self._validate_alarm_silence_definition(alarm_silence_definition,
                                                update=True)

        name = get_query_alarm_silence_definition_param(
            alarm_silence_definition, "name")
        description = get_query_alarm_silence_definition_description(
            alarm_silence_definition)
        start_time = get_query_alarm_silence_definition_start_time(
            alarm_silence_definition)
        silence_duration = get_query_alarm_silence_definition_silence_duration(
            alarm_silence_definition)

        result = self._alarm_silence_definition_update_or_patch(
            req.project_id, alarm_silence_definition_id, name, description,
            start_time, silence_duration, patch=False)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_patch(self, req, res, alarm_silence_definition_id):

        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_silence_definition = helpers.read_json_msg_body(req)

        # Optional args
        name = get_query_alarm_silence_definition_param(
            alarm_silence_definition, "name", return_none=True)
        description = get_query_alarm_silence_definition_description(
            alarm_silence_definition, return_none=True)
        start_time = get_query_alarm_silence_definition_start_time(
            alarm_silence_definition, return_none=True)
        silence_duration = get_query_alarm_silence_definition_silence_duration(
            alarm_silence_definition)

        result = self._alarm_silence_definition_update_or_patch(
            req.project_id, alarm_silence_definition_id, name, description,
            start_time, silence_duration, patch=True)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_delete(self, req, res, alarm_silence_definition_id):

        helpers.validate_authorization(req, self._default_authorized_roles)
        self._alarm_silence_definition_delete(req.project_id,
                                              alarm_silence_definition_id)
        res.status = falcon.HTTP_204

    def _alarm_silence_definition_delete(self, tenant_id,
                                         alarm_silence_definition_id):
        if not self._alarm_silence_definitions_repo\
                .delete_alarm_silence_definition(tenant_id,
                                                 alarm_silence_definition_id):
            raise falcon.HTTPNotFound

        self._send_alarm_silence_definition_deleted_event(
            alarm_silence_definition_id)

    def _send_alarm_silence_definition_deleted_event(
            self, alarm_silence_definition_id):
        alarm_silence_definition_deleted_event_msg = {
            u"alarm-silence-definition-deleted":
                {u"id": alarm_silence_definition_id}}
        self.send_event(self.events_message_queue,
                        alarm_silence_definition_deleted_event_msg)

    def _alarm_silence_definition_update_or_patch(
            self, tenant_id, alarm_silence_definition_id, name, description,
            start_time, silence_duration, patch):
        if name:
            self._validate_name_not_conflicting(
                tenant_id, name, expected_id=alarm_silence_definition_id)

        alarm_silence_definition_row = (
            self._alarm_silence_definitions_repo.
            update_or_patch_alarm_silence_definition(
                tenant_id,
                alarm_silence_definition_id,
                name,
                description,
                start_time,
                silence_duration,
                patch))

        result = self._build_alarm_silence_definition_show_result(
            alarm_silence_definition_row)
        # Not all of the passed in parameters will be set if this called
        # from on_patch vs on_update. The alarm-silence-definition-updated
        # event MUST have all of the fields set so use the dict built from the
        # data returned from the database
        alarm_silence_definition_event_dict = (
            {u'tenantId': tenant_id,
             u'id': alarm_silence_definition_id,
             u'name': result['name'],
             u'description': result['description'],
             u'matchers': result['matchers'],
             u'start_time': result['start_time'],
             u'silence_duration': result['silence_duration']})

        alarm_silence_definition_updated_event = (
            {u'alarm-silence-definition-updated':
             alarm_silence_definition_event_dict})

        self.send_event(self.events_message_queue,
                        alarm_silence_definition_updated_event)

        return result

    def _validate_alarm_silence_definition(self, alarm_silence_definition,
                                           update=False):
        try:
            schema_silence_definition.validate(alarm_silence_definition,
                                               update=update)
        except Exception as ex:
            LOG.debug(ex)
            raise HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))

    @resource.resource_try_catch_block
    def _alarm_silence_definition_create(self, tenant_id, name, description,
                                         matchers, start_time,
                                         silence_duration):
        self._validate_name_not_conflicting(tenant_id, name)

        alarm_silence_definition_id = (
            self._alarm_silence_definitions_repo
                .create_alarm_silence_definition(tenant_id, name, description,
                                                 matchers, start_time,
                                                 silence_duration))

        self._send_alarm_silence_definition_created_event(
            tenant_id, alarm_silence_definition_id, name, matchers,
            start_time, silence_duration)

        result = (
            {u'id': alarm_silence_definition_id,
             u'name': name,
             u'description': description,
             u'matchers': matchers,
             u'start_time': start_time,
             u'silence_duration': silence_duration})

        return result

    def _alarm_silence_definition_show(self, tenant_id, silence_definition_id):

        alarm_silence_definition_row = (
            self._alarm_silence_definitions_repo.get_alarm_silence_definition(
                tenant_id, silence_definition_id))

        return self._build_alarm_silence_definition_show_result(
            alarm_silence_definition_row)

    def _build_alarm_silence_definition_show_result(
            self, alarm_silence_definition_row):
        matchers = get_comma_separated_str_as_dict(
            alarm_silence_definition_row['matchers'])

        start_time = alarm_silence_definition_row['start_time']

        silence_duration = alarm_silence_definition_row['silence_duration']

        result = {
            u'matchers': matchers,
            u'start_time': start_time,
            u'silence_duration': silence_duration,
            u'id': alarm_silence_definition_row['id'],
            u'name': alarm_silence_definition_row['name'],
            u'description': alarm_silence_definition_row['description']}

        return result

    def _alarm_silence_definition_list(self, tenant_id, name, req_uri, offset,
                                       limit):
        now = datetime.datetime.utcnow()
        alarm_silence_definition_rows = (
            self._alarm_silence_definitions_repo.get_alarm_silence_definitions(
                tenant_id, name, offset, limit))
        result = []
        for alarm_silence_definition_row in alarm_silence_definition_rows:
            matchers = get_comma_separated_str_as_dict(
                alarm_silence_definition_row['matchers'])

            asm = {u'id': alarm_silence_definition_row['id'],
                   u'name': alarm_silence_definition_row['name'],
                   u'description': alarm_silence_definition_row['description']
                   if (alarm_silence_definition_row['description'])
                   else '',
                   u'matchers': matchers,
                   u'start_time': alarm_silence_definition_row['start_time']
                   if (alarm_silence_definition_row['start_time'])
                   else u'{}'.format(now),
                   u'silence_duration': alarm_silence_definition_row[
                       'silence_duration']
                   if (alarm_silence_definition_row['silence_duration'])
                   else u'null'}

            helpers.add_links_to_resource(asm, req_uri)
            result.append(asm)

        result = helpers.paginate_alarming(result, req_uri, limit)
        return result

    def _validate_name_not_conflicting(self, tenant_id, name,
                                       expected_id=None):
        alarm_silence_definitions = self._alarm_silence_definitions_repo.\
            get_alarm_silence_definitions(tenant_id=tenant_id, name=name,
                                          offset=None, limit=0)
        if alarm_silence_definitions:
            if not expected_id:
                LOG.warning("Found existing alarm silence definition for {} "
                            "with tenant_id {}".format(name, tenant_id))
                raise exceptions.AlreadyExistsException(
                    "An alarm silence definition with the name {} already "
                    "exists.".format(name))

            found_silence_definition_id = alarm_silence_definitions[0]['id']
            if found_silence_definition_id != expected_id:
                LOG.warning("Found existing alarm silence definition for {} "
                            "with tenant_id {} with unexpected id {}".
                            format(name, tenant_id,
                                   found_silence_definition_id))
                raise exceptions.AlreadyExistsException(
                    "An alarm silence definition with the name {} already "
                    "exists with id {}".format(name,
                                               found_silence_definition_id))

    def _send_alarm_silence_definition_created_event(
            self, tenant_id, alarm_silence_definition_id, name, matchers,
            start_time, silence_duration):
        alarm_silence_definition_created_event_msg = {
            u'alarm-silence-definition-created':
                {u'tenantId': tenant_id,
                 u'id': alarm_silence_definition_id,
                 u'name': name,
                 u'matchers': matchers,
                 u'start_time': start_time,
                 u'silence_duration': silence_duration
                 }
        }
        self.send_event(self.events_message_queue,
                        alarm_silence_definition_created_event_msg)


def get_query_alarm_silence_definition_param(
        alarm_silence_definition, param, return_none=False):
    try:
        if param in alarm_silence_definition:
            param_value = alarm_silence_definition[param]
            return param_value
        else:
            if return_none:
                return None
            else:
                raise Exception("Missing silence definition {}".format(param))
    except Exception as ex:
        LOG.debug(ex)
        raise HTTPUnprocessableEntityError('Unprocessable Entity', ex.message)


def get_query_alarm_silence_definition_description(alarm_silence_definition,
                                                   return_none=False):
    if 'description' in alarm_silence_definition:
        return alarm_silence_definition['description']
    else:
        if return_none:
            return None
        else:
            return ''


def get_query_alarm_silence_definition_start_time(alarm_silence_definition,
                                                  return_none=False):
    if 'start_time' in alarm_silence_definition:
        start_time = alarm_silence_definition['start_time']
        return start_time
    else:
        if return_none:
            return None
        else:
            now = datetime.datetime.now().strftime(
                "%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'
            # default to current time
            return now


def get_query_alarm_silence_definition_silence_duration(
        alarm_silence_definition, return_none=False):
    if 'silence_duration' in alarm_silence_definition:
        silence_duration = alarm_silence_definition['silence_duration']
        return silence_duration
    else:
        if return_none:
            return None
        else:
            silence_duration = '10m'
            # default to current time
            return silence_duration


def get_comma_separated_str_as_list(comma_separated_str):
    if not comma_separated_str:
        return []
    else:
        return comma_separated_str.decode('utf8').split(',')


def get_comma_separated_str_as_dict(comma_separated_str):
    if not comma_separated_str:
        return {}
    else:
        return dict(part.split("=") for part in
                    comma_separated_str.decode('utf8').split(','))
