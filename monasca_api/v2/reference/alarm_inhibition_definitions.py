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

from monasca_api.api import alarm_inhibition_definitions_api_v2
from monasca_api.common.repositories import exceptions
from monasca_api.v2.common.exceptions import HTTPUnprocessableEntityError
from monasca_api.v2.common.schemas import (alarm_inhibition_definition_request_body_schema
                                           as schema_inhibition_definition)
import monasca_api.v2.common.validation as validation
from monasca_api.v2.reference import alarming
from monasca_api.v2.reference import helpers
from monasca_api.v2.reference import resource

LOG = log.getLogger(__name__)


class AlarmInhibitionDefinitions(alarm_inhibition_definitions_api_v2.
                                 AlarmInhibitionDefinitionsV2API, alarming.
                                 Alarming):

    def __init__(self):
        try:
            super(AlarmInhibitionDefinitions, self).__init__()
            self._region = cfg.CONF.region
            self._default_authorized_roles = (
                cfg.CONF.security.default_authorized_roles)
            self._get_alarm_inhibition_definitions_authorized_roles = (
                cfg.CONF.security.default_authorized_roles +
                cfg.CONF.security.read_only_authorized_roles)
            self._alarm_inhibition_definitions_repo = simport.load(
                cfg.CONF.repositories.alarm_inhibition_definitions_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    @resource.resource_try_catch_block
    def on_post(self, req, res):
        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_inhibition_definition = helpers.read_json_msg_body(req)
        self._validate_alarm_inhibition_definition(alarm_inhibition_definition)

        name = get_query_alarm_inhibition_definition_param(
            alarm_inhibition_definition, "name")
        equal = get_query_alarm_inhibition_definition_param(
            alarm_inhibition_definition, "equal")
        source_match = get_query_alarm_inhibition_definition_param(
            alarm_inhibition_definition, "source_match")
        target_match = get_query_alarm_inhibition_definition_param(
            alarm_inhibition_definition, "target_match")
        exclusions = get_query_alarm_inhibition_definition_exclusions(
            alarm_inhibition_definition, "exclusions")

        result = self._alarm_inhibition_definition_create(req.project_id, name,
                                                          equal, source_match,
                                                          target_match,
                                                          exclusions)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_201

    @resource.resource_try_catch_block
    def on_get(self, req, res, alarm_inhibition_definition_id=None):
        if alarm_inhibition_definition_id is None:
            helpers.validate_authorization(
                req, self._get_alarm_inhibition_definitions_authorized_roles)

            name = helpers.get_query_name(req)
            offset = helpers.get_query_param(req, 'offset')
            if offset is not None and not isinstance(offset, int):
                try:
                    offset = int(offset)
                except Exception:
                    raise HTTPUnprocessableEntityError(
                        'Unprocessable Entity, Offset value {} must be an '
                        'integer'.format(offset))

            result = self._alarm_inhibition_definition_list(
                req.project_id, name, req.uri, offset, req.limit)

            res.body = helpers.dumpit_utf8(result)
            res.status = falcon.HTTP_200

        else:
            helpers.validate_authorization(
                req, self._get_alarm_inhibition_definitions_authorized_roles)

            result = self._alarm_inhibition_definition_show(
                req.project_id, alarm_inhibition_definition_id)

            helpers.add_links_to_resource(
                result, re.sub('/' + alarm_inhibition_definition_id, '',
                               req.uri))
            res.body = helpers.dumpit_utf8(result)
            res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_put(self, req, res, alarm_inhibition_definition_id):

        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_inhibition_definition = helpers.read_json_msg_body(req)

        self._validate_alarm_inhibition_definition(alarm_inhibition_definition,
                                                   require_all=True)

        name = get_query_alarm_inhibition_definition_param(
            alarm_inhibition_definition, "name")
        equal = get_query_alarm_inhibition_definition_param(
            alarm_inhibition_definition, "equal")
        source_match = get_query_alarm_inhibition_definition_param(
            alarm_inhibition_definition, "source_match")
        target_match = get_query_alarm_inhibition_definition_param(
            alarm_inhibition_definition, "target_match")
        exclusions = get_query_alarm_inhibition_definition_exclusions(
            alarm_inhibition_definition)

        result = self._alarm_inhibition_definition_update_or_patch(
            req.project_id, alarm_inhibition_definition_id, name, equal,
            source_match, target_match, exclusions, patch=False)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_patch(self, req, res, alarm_inhibition_definition_id):

        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_inhibition_definition = helpers.read_json_msg_body(req)

        # Optional args
        name = get_query_alarm_inhibition_definition_param(
            alarm_inhibition_definition, "name", return_none=True)
        equal = get_query_alarm_inhibition_definition_param(
            alarm_inhibition_definition, "equal", return_none=True)
        source_match = get_query_alarm_inhibition_definition_param(
            alarm_inhibition_definition, "source_match", return_none=True)
        target_match = get_query_alarm_inhibition_definition_param(
            alarm_inhibition_definition, "target_match", return_none=True)
        exclusions = get_query_alarm_inhibition_definition_exclusions(
            alarm_inhibition_definition, return_none=True)

        result = self._alarm_inhibition_definition_update_or_patch(
            req.project_id, alarm_inhibition_definition_id, name, equal,
            source_match, target_match, exclusions, patch=True)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_delete(self, req, res, alarm_inhibition_definition_id):

        helpers.validate_authorization(req, self._default_authorized_roles)
        self._alarm_inhibition_definition_delete(
            req.project_id, alarm_inhibition_definition_id)
        res.status = falcon.HTTP_204

    def _alarm_inhibition_definition_delete(
            self, tenant_id, alarm_inhibition_definition_id):
        if not self._alarm_inhibition_definitions_repo\
                .delete_alarm_inhibition_definition(
                tenant_id, alarm_inhibition_definition_id):
            raise falcon.HTTPNotFound

        self._send_alarm_inhibition_definition_deleted_event(
            alarm_inhibition_definition_id)

    def _send_alarm_inhibition_definition_deleted_event(
            self, alarm_inhibition_definition_id):
        alarm_inhibition_definition_deleted_event_msg = {
            u"alarm-inhibition-definition-deleted": {
                u"id": alarm_inhibition_definition_id}}
        self.send_event(self.events_message_queue,
                        alarm_inhibition_definition_deleted_event_msg)

    def _alarm_inhibition_definition_update_or_patch(
            self, tenant_id, alarm_inhibition_definition_id, name, equal,
            source_match, target_match, exclusions, patch):
        if name:
            self._validate_name_not_conflicting(
                tenant_id, name, expected_id=alarm_inhibition_definition_id)

        alarm_inhibition_definition_row = (
            self._alarm_inhibition_definitions_repo.
            update_or_patch_alarm_inhibition_definition(
                tenant_id,
                alarm_inhibition_definition_id,
                name,
                equal,
                source_match,
                target_match,
                exclusions,
                patch))

        result = self._build_alarm_inhibition_definition_show_result(
            alarm_inhibition_definition_row)

        # Not all of the passed in parameters will be set if this called
        # from on_patch vs on_update. The alarm-inhibition-definition-updated
        # event MUST have all of the fields set so use the dict built from the
        # data returned from the database.
        alarm_inhibition_definition_event_dict = (
            {u'tenantId': tenant_id,
             u'id': alarm_inhibition_definition_id,
             u'name': result['name'],
             u'equal': result['equal'],
             u'source_match': result['source_match'],
             u'target_match': result['target_match'],
             u'exclusions': result['exclusions']})

        alarm_inhibition_definition_updated_event = (
            {u'alarm-inhibition-definition-updated':
             alarm_inhibition_definition_event_dict})

        self.send_event(self.events_message_queue,
                        alarm_inhibition_definition_updated_event)

        return result

    def _validate_alarm_inhibition_definition(self, alarm_inhibition_definition,
                                              require_all=False):
        try:
            schema_inhibition_definition.validate(alarm_inhibition_definition,
                                                  require_all=require_all)
            for key in alarm_inhibition_definition['equal']:
                validation.validate_matcher_key(key)

            validation.validate_matchers(
                alarm_inhibition_definition['source_match'])

            validation.validate_matchers(
                alarm_inhibition_definition['target_match'])

        except Exception as ex:
            LOG.debug(ex)
            raise HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))

    @resource.resource_try_catch_block
    def _alarm_inhibition_definition_create(self, tenant_id, name, equal,
                                            source_match, target_match,
                                            exclusions):
        self._validate_name_not_conflicting(tenant_id, name)
        alarm_inhibition_definition_id = (
            self._alarm_inhibition_definitions_repo
                .create_alarm_inhibition_definition(tenant_id, name, equal,
                                                    source_match, target_match,
                                                    exclusions))

        self._send_alarm_inhibition_definition_created_event(
            tenant_id, alarm_inhibition_definition_id, name, equal,
            source_match, target_match, exclusions)

        result = (
            {u'id': alarm_inhibition_definition_id,
             u'name': name,
             u'equal': equal,
             u'source_match': source_match,
             u'target_match': target_match,
             u'exclusions': exclusions
             })

        return result

    def _alarm_inhibition_definition_show(self, tenant_id, aid_id):

        alarm_inhibition_definition_row = (
            self._alarm_inhibition_definitions_repo.
            get_alarm_inhibition_definition(tenant_id, aid_id))

        return self._build_alarm_inhibition_definition_show_result(
            alarm_inhibition_definition_row)

    def _build_alarm_inhibition_definition_show_result(
            self, alarm_inhibition_definition_row):

        equal = get_comma_separated_str_as_list(
            alarm_inhibition_definition_row['equal'])
        source_match = get_comma_separated_str_as_list(
            alarm_inhibition_definition_row['source_match'])
        target_match = get_comma_separated_str_as_list(
            alarm_inhibition_definition_row['target_match'])
        exclusions = (alarm_inhibition_definition_row['exclusion']
                      if alarm_inhibition_definition_row['exclusion']
                      is not None else None)

        result = {
            u'id': alarm_inhibition_definition_row['id'].decode('utf8'),
            u'name': alarm_inhibition_definition_row['name'].decode('utf8'),
            u'equal': equal,
            u'source_match': source_match,
            u'target_match': target_match,
            u'exclusions': exclusions}

        return result

    def _alarm_inhibition_definition_list(self, tenant_id, name, req_uri,
                                          offset, limit):
        alarm_inhibition_definition_rows = (
            self._alarm_inhibition_definitions_repo.
            get_alarm_inhibition_definitions(tenant_id, name, offset, limit))
        result = []
        for row in alarm_inhibition_definition_rows:
            equal = get_comma_separated_str_as_list(row['equal'])
            source_match = get_comma_separated_str_as_list(row['source_match'])
            target_match = get_comma_separated_str_as_list(row['target_match'])
            exclusions = get_comma_separated_str_as_list(row['exclusion'])

            aim = {u'id': row['id'],
                   u'name': row['name'],
                   u'equal': equal,
                   u'source_match': source_match,
                   u'target_match': target_match,
                   u'exclusions': exclusions}

            helpers.add_links_to_resource(aim, req_uri)
            result.append(aim)
        return result

    def _validate_name_not_conflicting(self, tenant_id, name,
                                       expected_id=None):
        alarm_inhibition_definitions = \
            self._alarm_inhibition_definitions_repo.\
            get_alarm_inhibition_definitions(tenant_id=tenant_id, name=name,
                                             offset=None, limit=0)
        if alarm_inhibition_definitions:
            if not expected_id:
                LOG.warning("Found existing alarm inhibition definition for {}"
                            " with tenant_id {}".format(name, tenant_id))
                raise exceptions.AlreadyExistsException(
                    "An alarm inhibition definition with the name {} already "
                    "exists"
                    .format(name))

            found_inhibition_definition_id = \
                alarm_inhibition_definitions[0]['id']
            if found_inhibition_definition_id != expected_id:
                LOG.warning("Found existing alarm inhibition definition for {}"
                            " with tenant_id {} with unexpected id {}".
                            format(name, tenant_id,
                                   found_inhibition_definition_id))
                raise exceptions.AlreadyExistsException(
                    "An alarm inhibition definition with the name {} already "
                    "exists with id {}".format(name,
                                               found_inhibition_definition_id))

    def _send_alarm_inhibition_definition_created_event(
            self, tenant_id, alarm_inhibition_definition_id, name, equal,
            source_match, target_match, exclusions):
        alarm_inhibition_definition_created_event_msg = {
            u'alarm-inhibition-definition-created':
                {u'tenantId': tenant_id,
                 u'id': alarm_inhibition_definition_id,
                 u'name': name,
                 u'equal': equal,
                 u'source_match': source_match,
                 u'target_match': target_match,
                 u'exclusions': exclusions
                 }
        }
        self.send_event(self.events_message_queue,
                        alarm_inhibition_definition_created_event_msg)


def get_query_alarm_inhibition_definition_exclusions(alarm_inhibition_definition,
                                                     return_none=False):
    if 'exclusions' in alarm_inhibition_definition:
        exclusions = alarm_inhibition_definition['exclusions']
        return exclusions
    else:
        if return_none:
            return None
        else:
            return []


def get_query_alarm_inhibition_definition_param(alarm_inhibition_definition,
                                                param, return_none=False):
    try:
        if param in alarm_inhibition_definition:
            param_value = alarm_inhibition_definition[param]
            return param_value
        else:
            if return_none:
                return None
            else:
                raise Exception("Missing inhibition definition {}".format(
                    param))
    except Exception as ex:
        LOG.debug(ex)
        raise HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))


def get_comma_separated_str_as_list(comma_separated_str):
    if not comma_separated_str:
        return []
    else:
        return comma_separated_str.decode('utf8').split(',')
