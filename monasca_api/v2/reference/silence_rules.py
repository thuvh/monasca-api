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
import monasca_api.v2.common.exceptions as exception
import re

from monasca_common.monasca_query_language import aql_parser
from monasca_common.simport import simport
from oslo_config import cfg
from oslo_log import log

from monasca_api.api import silence_rules_api_v2
from monasca_api.common.repositories import constants
from monasca_api.common.repositories import exceptions
from monasca_api.v2.common.exceptions import HTTPUnprocessableEntityError
from monasca_api.v2.common.schemas import (
    silence_rule_request_body_schema as schema_silence_rule)
import monasca_api.v2.common.validation as validation
from monasca_api.v2.reference import alarming
from monasca_api.v2.reference import helpers
from monasca_api.v2.reference import resource

LOG = log.getLogger(__name__)


class SilenceRules(silence_rules_api_v2.SilenceRulesV2API, alarming.Alarming):

    def __init__(self):
        try:
            super(SilenceRules, self).__init__()
            self.rule_updates_message_queue = simport.load(
                cfg.CONF.messaging.driver)(cfg.CONF.kafka.rule_updates_topic)
            self._region = cfg.CONF.region
            self._default_authorized_roles = (
                cfg.CONF.security.default_authorized_roles)
            self._get_silence_rules_authorized_roles = (
                cfg.CONF.security.default_authorized_roles +
                cfg.CONF.security.read_only_authorized_roles)
            self._silence_rules_repo = simport.load(
                cfg.CONF.repositories.silence_rules_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    @resource.resource_try_catch_block
    def on_post(self, req, res):
        helpers.validate_authorization(req, self._default_authorized_roles)

        silence_rule = helpers.from_json(req)

        self._validate_silence_rule(silence_rule)

        name = get_query_silence_rule_param(
            silence_rule, "name")
        description = get_query_silence_rule_description(
            silence_rule)
        expression = get_query_silence_rule_param(
            silence_rule, "expression")
        start_time = get_query_silence_rule_start_time(
            silence_rule)
        silence_duration = get_query_silence_rule_silence_duration(silence_rule)

        result = self._silence_rule_create(req.project_id, name, expression, description,
                                           start_time, silence_duration)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.to_json(result)
        res.status = falcon.HTTP_201

    @resource.resource_try_catch_block
    def on_get(self, req, res, silence_rule_id=None):
        helpers.validate_authorization(
            req, self._get_silence_rules_authorized_roles)
        if silence_rule_id is None:
            name = helpers.get_query_name(req)
            offset = helpers.get_query_param(req, 'offset')
            if offset is not None and not isinstance(offset, int):
                try:
                    offset = int(offset)
                except Exception:
                    raise exception.HTTPUnprocessableEntityError(
                        'Unprocessable Entity, Offset value {} must be an '
                        'integer'.format(offset))

            result = self._silence_rule_list(
                req.project_id, name, req.uri, offset, req.limit)

            res.body = helpers.to_json(result)
            res.status = falcon.HTTP_200

        else:
            helpers.validate_authorization(
                req, self._get_silence_rules_authorized_roles)

            result = self._silence_rule_show(
                req.project_id, silence_rule_id)

            helpers.add_links_to_resource(
                result, re.sub('/' + silence_rule_id, '', req.uri))
            res.body = helpers.to_json(result)
            res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_put(self, req, res, silence_rule_id=None):
        if not silence_rule_id:
            raise HTTPUnprocessableEntityError(
                'Unprocessable Entity', 'Silence rule id is not provided')
        helpers.validate_authorization(req, self._default_authorized_roles)

        silence_rule = helpers.from_json(req)

        self._validate_silence_rule(silence_rule, require_all=True)

        name = get_query_silence_rule_param(
            silence_rule, "name")
        description = get_query_silence_rule_description(
            silence_rule)
        expression = get_query_silence_rule_param(
            silence_rule, "expression")
        start_time = get_query_silence_rule_start_time(
            silence_rule)
        silence_duration = get_query_silence_rule_silence_duration(
            silence_rule)

        result = self._silence_rule_update_or_patch(
            req.project_id, silence_rule_id, name, expression, description,
            start_time, silence_duration, patch=False)

        helpers.add_links_to_resource(
            result, re.sub('/' + silence_rule_id, '', req.uri))
        res.body = helpers.to_json(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_patch(self, req, res, silence_rule_id=None):
        if not silence_rule_id:
            raise HTTPUnprocessableEntityError(
                'Unprocessable Entity', 'Silence rule id is not provided')
        helpers.validate_authorization(req, self._default_authorized_roles)

        silence_rule = helpers.from_json(req)

        # Optional args
        name = get_query_silence_rule_param(
            silence_rule, "name", return_none=True)
        description = get_query_silence_rule_description(
            silence_rule, return_none=True)
        expression = get_query_silence_rule_param(
            silence_rule, "expression", return_none=True)
        start_time = get_query_silence_rule_start_time(
            silence_rule, return_none=True)
        silence_duration = get_query_silence_rule_silence_duration(
            silence_rule)

        result = self._silence_rule_update_or_patch(
            req.project_id, silence_rule_id, name, expression, description,
            start_time, silence_duration, patch=True)

        helpers.add_links_to_resource(
            result, re.sub('/' + silence_rule_id, '', req.uri))
        res.body = helpers.to_json(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_delete(self, req, res, silence_rule_id):

        helpers.validate_authorization(req, self._default_authorized_roles)
        self._silence_rule_delete(req.project_id, silence_rule_id)
        res.status = falcon.HTTP_204

    def _silence_rule_delete(self, tenant_id, silence_rule_id):
        if not self._silence_rules_repo.delete_silence_rule(tenant_id,
                                                            silence_rule_id):
            raise falcon.HTTPNotFound

        self._send_silence_rule_deleted_event(silence_rule_id)

    def _send_silence_rule_deleted_event(
            self, silence_rule_id):
        silence_rule_deleted_event_msg = {
            u"silence-rule-deleted": {u"id": silence_rule_id}}
        self.send_event(self.rule_updates_message_queue,
                        silence_rule_deleted_event_msg)

    def _silence_rule_update_or_patch(
            self, tenant_id, silence_rule_id, name, expression, description,
            start_time, silence_duration, patch):
        if name:
            self._validate_name_not_conflicting(
                tenant_id, name, expected_id=silence_rule_id)

        silence_rule_row = (
            self._silence_rules_repo.
            update_or_patch_silence_rule(
                tenant_id,
                silence_rule_id,
                name,
                expression,
                description,
                start_time,
                silence_duration,
                patch))

        result = self._build_silence_rule_show_result(
            silence_rule_row)
        # Not all of the passed in parameters will be set if this called
        # from on_patch vs on_update. The silence-rule-updated
        # event MUST have all of the fields set so use the dict built from the
        # data returned from the database
        try:
            result_expression = aql_parser.RuleExpressionParser(str(result['expression']))
            result_expression = result_expression.parse()[0].get_struct("silence")
        except Exception as ex:
            LOG.debug(ex)
            raise exception.HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))
        silence_rule_event_dict = (
            {u'tenantId': tenant_id,
             u'id': silence_rule_id,
             u'name': result['name'],
             u'description': result['description'],
             u'matchers': result_expression['matchers'],
             u'start_time': result['start_time'],
             u'silence_duration': result['silence_duration']})

        silence_rule_updated_event = (
            {u'silence-rule-updated':
             silence_rule_event_dict})

        self.send_event(self.rule_updates_message_queue,
                        silence_rule_updated_event)

        return result

    def _validate_silence_rule(self, silence_rule, require_all=False):
        try:
            schema_silence_rule.validate(silence_rule, require_all=require_all)
            validation.validate_expression(silence_rule['expression'])
        except Exception as ex:
            LOG.debug(ex)
            raise exception.HTTPUnprocessableEntityError('Unprocessable Entity',
                                                         str(ex))

    def _silence_rule_create(self, tenant_id, name, expression, description,
                             start_time, silence_duration):
        self._validate_name_not_conflicting(tenant_id, name)

        silence_rule_id = (
            self._silence_rules_repo
                .create_silence_rule(tenant_id, name, expression, description,
                                     start_time, silence_duration))

        self._send_silence_rule_created_event(
            tenant_id, silence_rule_id, name, expression,
            start_time, silence_duration)

        result = (
            {u'id': silence_rule_id,
             u'name': name,
             u'description': description,
             u'expression': expression,
             u'start_time': start_time,
             u'silence_duration': silence_duration})

        return result

    def _silence_rule_show(self, tenant_id, silence_definition_id):

        silence_rule_row = (
            self._silence_rules_repo.get_silence_rule(
                tenant_id, silence_definition_id))

        return self._build_silence_rule_show_result(silence_rule_row)

    def _build_silence_rule_show_result(self, silence_rule_row):
        result = {
            u'expression': silence_rule_row['expression'],
            u'start_time': silence_rule_row['start_time'],
            u'silence_duration': silence_rule_row['silence_duration'],
            u'id': silence_rule_row['id'],
            u'name': silence_rule_row['name'],
            u'description': silence_rule_row['description']}
        return result

    def _silence_rule_list(self, tenant_id, name, req_uri, offset, limit):
        now = datetime.datetime.utcnow()
        silence_rule_rows = (
            self._silence_rules_repo.get_silence_rules(
                tenant_id, name, offset, limit))
        result = []
        for silence_rule_row in silence_rule_rows:
            expression = silence_rule_row['expression']

            sr = {u'id': silence_rule_row['id'],
                  u'name': silence_rule_row['name'],
                  u'description': silence_rule_row['description']
                  if silence_rule_row['description']
                  else constants.RULE_DESCRIPTION,
                  u'expression': expression,
                  u'start_time': silence_rule_row['start_time']
                  if silence_rule_row['start_time']
                  else u'{}'.format(now),
                  u'silence_duration': silence_rule_row['silence_duration']
                  if silence_rule_row['silence_duration']
                  else u'null'}

            helpers.add_links_to_resource(sr, req_uri)
            result.append(sr)

        result = helpers.paginate_alarming(result, req_uri, limit)
        return result

    def _validate_name_not_conflicting(self, tenant_id, name,
                                       expected_id=None):
        silence_rules = self._silence_rules_repo.\
            get_silence_rules(tenant_id=tenant_id, name=name, offset=None,
                              limit=None)
        if silence_rules:
            if not expected_id:
                LOG.warning("Found existing silence rule for {} "
                            "with tenant_id {}".format(name, tenant_id))
                raise exceptions.AlreadyExistsException(
                    "An silence rule with the name {} already "
                    "exists.".format(name))

            found_silence_definition_id = silence_rules[0]['id']
            if found_silence_definition_id != expected_id:
                LOG.warning("Found existing silence rule for {} "
                            "with tenant_id {} with unexpected id {}".
                            format(name, tenant_id,
                                   found_silence_definition_id))
                raise exceptions.AlreadyExistsException(
                    "An silence rule with the name {} already "
                    "exists with id {}".format(name,
                                               found_silence_definition_id))

    def _send_silence_rule_created_event(
            self, tenant_id, silence_rule_id, name, expression,
            start_time, silence_duration):
        try:
            result_expression = aql_parser.RuleExpressionParser(str(expression)).parse()
            result_expression = result_expression[0].get_struct("silence")
        except Exception as ex:
            LOG.debug(ex)
            raise exception.HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))
        silence_rule_created_event_msg = {
            u'silence-rule-created':
                {u'tenantId': tenant_id,
                 u'id': silence_rule_id,
                 u'name': name,
                 u'matchers': result_expression['matchers'],
                 u'start_time': start_time,
                 u'silence_duration': silence_duration
                 }
        }
        self.send_event(self.rule_updates_message_queue,
                        silence_rule_created_event_msg)


def get_query_silence_rule_param(silence_rule, param, return_none=False):
    try:
        if param in silence_rule:
            param_value = silence_rule[param]
            return param_value
        else:
            if return_none:
                return None
            else:
                raise Exception("Missing silence rule {}".format(param))
    except Exception as ex:
        LOG.debug(ex)
        raise exception.HTTPUnprocessableEntityError('Unprocessable Entity',
                                                     ex.message)


def get_query_silence_rule_description(silence_rule, return_none=False):
    if 'description' in silence_rule:
        return silence_rule['description']
    elif return_none:
        return None
    else:
        return constants.RULE_DESCRIPTION


def get_query_silence_rule_start_time(silence_rule, return_none=False):
    if 'start_time' in silence_rule:
        start_time = silence_rule['start_time']
        return start_time
    elif return_none:
        return None
    else:
        return datetime.datetime.utcnow()


def get_query_silence_rule_silence_duration(
        silence_rule, return_none=False):
    if 'silence_duration' in silence_rule:
        silence_duration = silence_rule['silence_duration']
        return silence_duration
    elif return_none:
        return None
    else:
        return constants.SILENCE_RULE_SILENCE_DURATION
