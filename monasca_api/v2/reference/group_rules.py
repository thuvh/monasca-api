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
import monasca_api.v2.common.exceptions as exception
import re

from monasca_common.monasca_query_language import aql_parser
from monasca_common.simport import simport
from oslo_config import cfg
from oslo_log import log

from monasca_api.api import group_rules_api_v2
from monasca_api.common.repositories import constants
from monasca_api.common.repositories import exceptions
from monasca_api.v2.common.schemas import (
    group_rule_request_body_schema as schema_group_rule)
import monasca_api.v2.common.validation as validation
from monasca_api.v2.reference import alarming
from monasca_api.v2.reference import helpers
from monasca_api.v2.reference import resource

LOG = log.getLogger(__name__)


class GroupRules(group_rules_api_v2.GroupRulesV2API, alarming.Alarming):

    def __init__(self):
        try:
            super(GroupRules, self).__init__()
            self._region = cfg.CONF.region
            self._default_authorized_roles = (
                cfg.CONF.security.default_authorized_roles)
            self._get_group_rules_authorized_roles = (
                cfg.CONF.security.default_authorized_roles +
                cfg.CONF.security.read_only_authorized_roles)
            self._group_rules_repo = simport.load(
                cfg.CONF.repositories.group_rules_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    @resource.resource_try_catch_block
    def on_post(self, req, res):
        helpers.validate_authorization(req, self._default_authorized_roles)

        group_rule = helpers.from_json(req)

        self._validate_group_rule(group_rule)

        name = get_query_group_rule_param(group_rule, "name")
        description = get_query_group_rule_description(
            group_rule)
        expression = get_query_group_rule_param(
            group_rule, "expression")
        group_wait = get_query_group_rule_group_wait(
            group_rule)
        repeat_interval = get_query_group_rule_repeat_interval(
            group_rule)
        alarm_actions = get_query_group_rule_actions(
            group_rule, "alarm_actions")
        ok_actions = get_query_group_rule_actions(
            group_rule, "ok_actions")
        undetermined_actions = get_query_group_rule_actions(
            group_rule, "undetermined_actions")

        result = self._group_rule_create(req.project_id, name, expression,
                                         description, group_wait, repeat_interval,
                                         alarm_actions, ok_actions, undetermined_actions)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.to_json(result)
        res.status = falcon.HTTP_201

    @resource.resource_try_catch_block
    def on_get(self, req, res, group_rule_id=None):
        helpers.validate_authorization(
            req, self._get_group_rules_authorized_roles)

        if not group_rule_id:
            name = helpers.get_query_name(req)
            offset = helpers.get_query_param(req, 'offset')
            if offset is not None and not isinstance(offset, int):
                try:
                    offset = int(offset)
                except Exception:
                    raise exception.HTTPUnprocessableEntityError(
                        'Unprocessable Entity, Offset value {} must be an '
                        'integer'.format(offset))

            result = self._group_rule_list(
                req.project_id, name, req.uri, offset, req.limit)

        else:
            result = self._group_rule_show(
                req.project_id, group_rule_id)

            helpers.add_links_to_resource(
                result, re.sub('/' + group_rule_id, '', req.uri))

        res.body = helpers.to_json(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_put(self, req, res, group_rule_id):
        helpers.validate_authorization(req, self._default_authorized_roles)

        group_rule = helpers.from_json(req)

        self._validate_group_rule(group_rule, require_all=True)

        name = get_query_group_rule_param(
            group_rule, "name")
        description = get_query_group_rule_description(
            group_rule)
        expression = get_query_group_rule_param(
            group_rule, "expression")
        group_wait = get_query_group_rule_group_wait(
            group_rule)
        repeat_interval = get_query_group_rule_repeat_interval(
            group_rule)
        alarm_actions = get_query_group_rule_actions(
            group_rule, "alarm_actions")
        ok_actions = get_query_group_rule_actions(
            group_rule, "ok_actions")
        undetermined_actions = get_query_group_rule_actions(
            group_rule, "undetermined_actions")

        result = self._group_rule_update_or_patch(
            req.project_id, group_rule_id, name, description,
            expression, group_wait, repeat_interval, alarm_actions,
            ok_actions, undetermined_actions, patch=False)

        helpers.add_links_to_resource(
            result, re.sub('/' + group_rule_id, '', req.uri))
        res.body = helpers.to_json(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_patch(self, req, res, group_rule_id):

        helpers.validate_authorization(req, self._default_authorized_roles)

        group_rule = helpers.from_json(req)

        # Optional args
        name = get_query_group_rule_param(group_rule, "name", return_none=True)
        description = get_query_group_rule_description(
            group_rule, return_none=True)
        expression = get_query_group_rule_param(
            group_rule, "expression", return_none=True)
        group_wait = get_query_group_rule_group_wait(
            group_rule, return_none=True)
        repeat_interval = get_query_group_rule_repeat_interval(
            group_rule, return_none=True)
        alarm_actions = get_query_group_rule_actions(
            group_rule, "alarm_actions", return_none=True)
        ok_actions = get_query_group_rule_actions(
            group_rule, "ok_actions", return_none=True)
        undetermined_actions = get_query_group_rule_actions(
            group_rule, "undetermined_actions", return_none=True)

        result = self._group_rule_update_or_patch(
            req.project_id, group_rule_id, name, description,
            expression, group_wait, repeat_interval, alarm_actions,
            ok_actions, undetermined_actions, patch=True)

        helpers.add_links_to_resource(
            result, re.sub('/' + group_rule_id, '', req.uri))
        res.body = helpers.to_json(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_delete(self, req, res, group_rule_id):

        helpers.validate_authorization(req, self._default_authorized_roles)
        self._group_rule_delete(req.project_id, group_rule_id)
        res.status = falcon.HTTP_204

    def _group_rule_delete(self, tenant_id, group_rule_id):
        if not self._group_rules_repo\
                .delete_group_rule(tenant_id, group_rule_id):
            raise falcon.HTTPNotFound

        self._send_group_rule_deleted_event(
            group_rule_id)

    def _send_group_rule_deleted_event(self, group_rule_id):
        group_rule_deleted_event_msg = {
            u"group-rule-deleted": {u"id": group_rule_id}}
        self.send_event(self.events_message_queue,
                        group_rule_deleted_event_msg)

    def _group_rule_update_or_patch(
            self, tenant_id, group_rule_id, name, description,
            expression, group_wait, repeat_interval, alarm_actions,
            ok_actions, undetermined_actions, patch):

        if name:
            self._validate_name_not_conflicting(tenant_id, name,
                                                expected_id=group_rule_id)

        group_rule_row = (self._group_rules_repo.update_or_patch_group_rule(
            tenant_id, group_rule_id, name, expression, description,
            group_wait, repeat_interval, alarm_actions, ok_actions,
            undetermined_actions, patch))

        result = self._build_group_rule_show_result(group_rule_row)
        # Not all of the passed in parameters will be set if this called
        # from on_patch vs on_update. The group-rule-updated event
        # MUST have all of the fields set so use the dict built from the
        # data returned from the database.
        try:
            result_expression = aql_parser.RuleExpressionParser(str(result['expression']))
            result_expression = result_expression.parse()[0].get_struct("group")
        except Exception as ex:
            LOG.debug(ex)
            raise exception.HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))
        group_rule_event_dict = (
            {u'tenantId': tenant_id,
             u'id': group_rule_id,
             u'name': result['name'],
             u'description': result['description'],
             u'matchers': result_expression['matchers'],
             u'exclusions': result_expression['exclusions'],
             u'group_wait': result['group_wait'],
             u'repeat_interval': result['repeat_interval'],
             u'alarm_actions': alarm_actions,
             u'ok_actions': ok_actions,
             u'undetermined_actions': undetermined_actions})

        group_rule_updated_event = (
            {u'group-rule-updated':
             group_rule_event_dict})

        self.send_event(self.events_message_queue, group_rule_updated_event)
        return result

    def _validate_group_rule(self, group_rule, require_all=False):
        try:
            schema_group_rule.validate(group_rule, require_all=require_all)
            validation.validate_expression(group_rule['expression'])
        except Exception as ex:
            LOG.debug(ex)
            raise exception.HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))

    def _group_rule_create(self, tenant_id, name, expression, description, group_wait,
                           repeat_interval, alarm_actions, ok_actions, undetermined_actions):
        self._validate_name_not_conflicting(tenant_id, name)
        group_rule_id = (
            self._group_rules_repo
                .create_group_rule(tenant_id, name, expression, description, group_wait,
                                   repeat_interval, alarm_actions, ok_actions,
                                   undetermined_actions))

        self._send_group_rule_created_event(tenant_id, group_rule_id, name, expression,
                                            group_wait, repeat_interval, alarm_actions,
                                            ok_actions, undetermined_actions)
        result = (
            {u'alarm_actions': alarm_actions,
             u'ok_actions': ok_actions,
             u'undetermined_actions': undetermined_actions,
             u'repeat_interval': repeat_interval,
             u'group_wait': group_wait,
             u'expression': expression,
             u'id': group_rule_id,
             u'name': name,
             u'description': description})

        return result

    def _group_rule_show(self, tenant_id, group_rule_id):

        group_rule_row = (
            self._group_rules_repo.get_group_rule(tenant_id, group_rule_id))

        return self._build_group_rule_show_result(
            group_rule_row)

    def _build_group_rule_show_result(self, group_rule_row):

        alarm_actions_list = get_comma_separated_str_as_list(
            group_rule_row['alarm_actions'])

        ok_actions_list = get_comma_separated_str_as_list(
            group_rule_row['ok_actions'])

        undetermined_actions_list = get_comma_separated_str_as_list(
            group_rule_row['undetermined_actions'])

        group_wait = (group_rule_row['group_wait']
                      if group_rule_row['group_wait']
                      else constants.GROUP_RULE_GROUP_WAIT)
        repeat_interval = (group_rule_row['repeat_interval']
                           if group_rule_row['repeat_interval']
                           else constants.GROUP_RULE_REPEAT_INTERVAL)
        description = (group_rule_row['description']
                       if group_rule_row['description']
                       else constants.RULE_DESCRIPTION)

        result = {
            u'id': group_rule_row['id'],
            u'name': group_rule_row['name'],
            u'expression': group_rule_row['expression'],
            u'description': description,
            u'alarm_actions': alarm_actions_list,
            u'undetermined_actions': undetermined_actions_list,
            u'ok_actions': ok_actions_list,
            u'group_wait': group_wait,
            u'repeat_interval': repeat_interval}

        return result

    def _group_rule_list(self, tenant_id, name, req_uri, offset, limit):
        group_rule_rows = (
            self._group_rules_repo.get_group_rules(
                tenant_id, name, offset, limit))
        result = []
        for group_rule_row in group_rule_rows:
            expression = group_rule_row['expression']

            alarm_actions_list = get_comma_separated_str_as_list(
                group_rule_row['alarm_actions'])

            ok_actions_list = get_comma_separated_str_as_list(
                group_rule_row['ok_actions'])

            undetermined_actions_list = get_comma_separated_str_as_list(
                group_rule_row['undetermined_actions'])

            gr = {u'id': group_rule_row['id'],
                  u'name': group_rule_row['name'],
                  u'expression': expression,
                  u'description': group_rule_row['description']
                  if (group_rule_row['description']) else u'',
                  u'group_wait': group_rule_row['group_wait']
                  if (group_rule_row['group_wait']) else u'30s',
                  u'repeat_interval': group_rule_row['repeat_interval']
                  if (group_rule_row['repeat_interval']) else u'2h',
                  u'alarm_actions': alarm_actions_list,
                  u'ok_actions': ok_actions_list,
                  u'undetermined_actions': undetermined_actions_list}

            helpers.add_links_to_resource(gr, req_uri)
            result.append(gr)

        result = helpers.paginate_alarming(result, req_uri, limit)

        return result

    def _validate_name_not_conflicting(self, tenant_id, name,
                                       expected_id=None):
        group_rules = self._group_rules_repo.\
            get_group_rules(tenant_id=tenant_id, name=name, offset=None,
                            limit=None)
        if group_rules:
            if not expected_id:
                LOG.warning("Found existing group rule for {} "
                            "with tenant_id {}".format(name, tenant_id))
                raise exceptions.AlreadyExistsException(
                    "An group rule with the name {} already exists"
                    .format(name))

            found_group_rule_id = group_rules[0]['id']
            if found_group_rule_id != expected_id:
                LOG.warning("Found existing group rule for {} "
                            "with tenant_id {} with unexpected id {}".
                            format(name, tenant_id, found_group_rule_id))
                raise exceptions.AlreadyExistsException(
                    "An group rule with the name {} already "
                    "exists with id {}".format(name, found_group_rule_id))

    def _send_group_rule_created_event(self, tenant_id, group_rule_id, name,
                                       expression, group_wait, repeat_interval,
                                       alarm_actions, ok_actions, undetermined_actions):
        try:
            result_expression = aql_parser.RuleExpressionParser(str(expression)).parse()
            result_expression = result_expression[0].get_struct("group")
        except Exception as ex:
            LOG.debug(ex)
            raise exception.HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))
        group_rule_created_event_msg = {
            u'group-rule-created':
                {u'tenantId': tenant_id,
                 u'id': group_rule_id,
                 u'name': name,
                 u'matchers': result_expression['matchers'],
                 u'exclusions': result_expression['exclusions'],
                 u'group_wait': group_wait,
                 u'repeat_interval': repeat_interval,
                 u'alarm_actions': alarm_actions,
                 u'ok_actions': ok_actions,
                 u'undetermined_actions': undetermined_actions
                 }
        }
        self.send_event(self.events_message_queue,
                        group_rule_created_event_msg)


def get_query_group_rule_param(group_rule, param, return_none=False):
    try:
        if param in group_rule:
            param_value = group_rule[param]
            return param_value
        else:
            if return_none:
                return None
            else:
                raise Exception("Missing group rule {}".format(param))
    except Exception as ex:
        LOG.debug(ex)
        raise exception.HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))


def get_query_group_rule_description(group_rule, return_none=False):
    if 'description' in group_rule:
        return group_rule['description']
    elif return_none:
        return None
    else:
        return ''  # default to empty string


def get_query_group_rule_group_wait(group_rule, return_none=False):
    if 'group_wait' in group_rule:
        group_wait = group_rule['group_wait']
        return group_wait
    elif return_none:
        return None
    else:
        return constants.GROUP_RULE_GROUP_WAIT  # default to 30 seconds


def get_query_group_rule_repeat_interval(group_rule, return_none=False):
    if 'repeat_interval' in group_rule:
        repeat_interval = group_rule['repeat_interval']
        return repeat_interval
    elif return_none:
        return None
    else:
        return constants.GROUP_RULE_REPEAT_INTERVAL  # default to 2h


def get_query_group_rule_actions(group_rule, action_state, return_none=False):
    if action_state in group_rule:
        actions = group_rule[action_state]
        return actions
    elif return_none:
        return None
    else:
        return constants.GROUP_RULE_ACTIONS


def get_comma_separated_str_as_list(comma_separated_str):
    if not comma_separated_str:
        return []
    else:
        return comma_separated_str.decode('utf8').split(',')
