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

from monasca_api.api import inhibit_rules_api_v2
from monasca_api.common.repositories import constants
from monasca_api.common.repositories import exceptions
from monasca_api.v2.common.schemas import (inhibit_rule_request_body_schema as schema_inhibit_rule)
import monasca_api.v2.common.validation as validation
from monasca_api.v2.reference import group_rules
from monasca_api.v2.reference import helpers
from monasca_api.v2.reference import resource

LOG = log.getLogger(__name__)


class InhibitRules(inhibit_rules_api_v2.InhibitRulesV2API, group_rules.GroupRules):

    def __init__(self):
        try:
            super(InhibitRules, self).__init__()
            self._region = cfg.CONF.region
            self._default_authorized_roles = (
                cfg.CONF.security.default_authorized_roles)
            self._get_inhibit_rules_authorized_roles = (
                cfg.CONF.security.default_authorized_roles +
                cfg.CONF.security.read_only_authorized_roles)
            self._inhibit_rules_repo = simport.load(
                cfg.CONF.repositories.inhibit_rules_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    @resource.resource_try_catch_block
    def on_post(self, req, res):
        helpers.validate_authorization(req, self._default_authorized_roles)

        inhibit_rule = helpers.from_json(req)
        self._validate_inhibit_rule(inhibit_rule)

        name = get_query_inhibit_rule_param(
            inhibit_rule, "name")
        description = get_query_inhibit_rule_description(
            inhibit_rule)
        expression = get_query_inhibit_rule_param(
            inhibit_rule, "expression")

        result = self._inhibit_rule_create(req.project_id, name, expression,
                                           description)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.to_json(result)
        res.status = falcon.HTTP_201

    @resource.resource_try_catch_block
    def on_get(self, req, res, inhibit_rule_id=None):
        if inhibit_rule_id is None:
            helpers.validate_authorization(
                req, self._get_inhibit_rules_authorized_roles)

            name = helpers.get_query_name(req)
            offset = helpers.get_query_param(req, 'offset')
            if offset is not None and not isinstance(offset, int):
                try:
                    offset = int(offset)
                except Exception:
                    raise exception.HTTPUnprocessableEntityError(
                        'Unprocessable Entity, Offset value {} must be an '
                        'integer'.format(offset))

            result = self._inhibit_rule_list(
                req.project_id, name, req.uri, offset, req.limit)

        else:
            helpers.validate_authorization(
                req, self._get_inhibit_rules_authorized_roles)

            result = self._inhibit_rule_show(
                req.project_id, inhibit_rule_id)

            helpers.add_links_to_resource(
                result, re.sub('/' + inhibit_rule_id, '', req.uri))

        res.body = helpers.to_json(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_put(self, req, res, inhibit_rule_id):

        helpers.validate_authorization(req, self._default_authorized_roles)

        inhibit_rule = helpers.from_json(req)

        self._validate_inhibit_rule(inhibit_rule, require_all=True)

        name = get_query_inhibit_rule_param(
            inhibit_rule, "name")
        description = get_query_inhibit_rule_description(
            inhibit_rule)
        expression = get_query_inhibit_rule_param(
            inhibit_rule, "expression")

        result = self._inhibit_rule_update_or_patch(req.project_id,
                                                    inhibit_rule_id, name,
                                                    expression, description,
                                                    patch=False)

        helpers.add_links_to_resource(
            result, re.sub('/' + inhibit_rule_id, '', req.uri))
        res.body = helpers.to_json(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_patch(self, req, res, inhibit_rule_id):

        helpers.validate_authorization(req, self._default_authorized_roles)

        inhibit_rule = helpers.from_json(req)

        # Optional args
        name = get_query_inhibit_rule_param(
            inhibit_rule, "name", return_none=True)
        description = get_query_inhibit_rule_description(
            inhibit_rule, return_none=True)
        expression = get_query_inhibit_rule_param(
            inhibit_rule, "expression", return_none=True)

        result = self._inhibit_rule_update_or_patch(
            req.project_id, inhibit_rule_id, name, expression, description,
            patch=True)

        helpers.add_links_to_resource(
            result, re.sub('/' + inhibit_rule_id, '', req.uri))
        res.body = helpers.to_json(result)
        res.status = falcon.HTTP_200

    @resource.resource_try_catch_block
    def on_delete(self, req, res, inhibit_rule_id):

        helpers.validate_authorization(req, self._default_authorized_roles)
        self._inhibit_rule_delete(
            req.project_id, inhibit_rule_id)
        res.status = falcon.HTTP_204

    def _inhibit_rule_delete(
            self, tenant_id, inhibit_rule_id):
        if not self._inhibit_rules_repo\
                .delete_inhibit_rule(
                tenant_id, inhibit_rule_id):
            raise falcon.HTTPNotFound

        self._send_inhibit_rule_deleted_event(
            inhibit_rule_id)

    def _send_inhibit_rule_deleted_event(
            self, inhibit_rule_id):
        inhibit_rule_deleted_event_msg = {
            u"inhibit-rule-deleted": {u"id": inhibit_rule_id}}
        self.send_rule_event(self.rule_updates_message_queue,
                             inhibit_rule_deleted_event_msg)

    def _inhibit_rule_update_or_patch(self, tenant_id, inhibit_rule_id, name,
                                      expression, description, patch):
        if name:
            self._validate_name_not_conflicting(
                tenant_id, name, expected_id=inhibit_rule_id)

        inhibit_rule_row = (
            self._inhibit_rules_repo.
            update_or_patch_inhibit_rule(
                tenant_id,
                inhibit_rule_id,
                name,
                expression,
                description,
                patch))

        result = self._build_inhibit_rule_show_result(
            inhibit_rule_row)

        # Not all of the passed in parameters will be set if this called
        # from on_patch vs on_update. The inhibit-rule-updated
        # event MUST have all of the fields set so use the dict built from the
        # data returned from the database.
        try:
            result_expression = aql_parser.RuleExpressionParser(str(result['expression']))
            result_expression = result_expression.parse()[0].get_struct("inhibit")
        except Exception as ex:
            LOG.debug(ex)
            raise exception.HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))
        inhibit_rule_event_dict = (
            {u'tenantId': tenant_id,
             u'id': inhibit_rule_id,
             u'name': result['name'],
             u'description': result['description'],
             u'source_match': result_expression['source_match'],
             u'target_match': result_expression['target_match'],
             u'equal': result_expression['equal'],
             u'exclusions': result_expression['exclusions']})

        inhibit_rule_updated_event = (
            {u'inhibit-rule-updated':
             inhibit_rule_event_dict})

        self.send_rule_event(self.rule_updates_message_queue,
                             inhibit_rule_updated_event)

        return result

    def _validate_inhibit_rule(self, inhibit_rule, require_all=False):
        try:
            schema_inhibit_rule.validate(inhibit_rule, require_all=require_all)
            validation.validate_expression(inhibit_rule['expression'])
        except Exception as ex:
            LOG.debug(ex)
            raise exception.HTTPUnprocessableEntityError(
                'Unprocessable Entity', str(ex))

    def _inhibit_rule_create(self, tenant_id, name, expression, description):
        self._validate_name_not_conflicting(tenant_id, name)
        inhibit_rule_id = (
            self._inhibit_rules_repo
                .create_inhibit_rule(tenant_id, name, expression, description))

        self._send_inhibit_rule_created_event(tenant_id, inhibit_rule_id, name,
                                              expression)

        result = (
            {u'id': inhibit_rule_id,
             u'name': name,
             u'description': description,
             u'expression': expression})

        return result

    def _inhibit_rule_show(self, tenant_id, aid_id):

        inhibit_rule_row = (
            self._inhibit_rules_repo.
            get_inhibit_rule(tenant_id, aid_id))

        return self._build_inhibit_rule_show_result(
            inhibit_rule_row)

    def _build_inhibit_rule_show_result(self, inhibit_rule_row):
        result = {
            u'id': inhibit_rule_row['id'],
            u'name': inhibit_rule_row['name'],
            u'description': inhibit_rule_row['description'],
            u'expression': inhibit_rule_row['expression']}

        return result

    def _inhibit_rule_list(self, tenant_id, name, req_uri, offset, limit):
        inhibit_rule_rows = (
            self._inhibit_rules_repo.
            get_inhibit_rules(tenant_id, name, offset, limit))
        result = []
        for row in inhibit_rule_rows:
            ir = {u'id': row['id'],
                  u'name': row['name'],
                  u'description': row['description'],
                  u'expression': row['expression']}

            helpers.add_links_to_resource(ir, req_uri)
            result.append(ir)

        result = helpers.paginate_alarming(result, req_uri, limit)

        return result

    def _validate_name_not_conflicting(self, tenant_id, name,
                                       expected_id=None):
        inhibit_rules = \
            self._inhibit_rules_repo.\
            get_inhibit_rules(tenant_id=tenant_id, name=name,
                              offset=None, limit=None)
        if inhibit_rules:
            if not expected_id:
                LOG.warning("Found existing inhibit rule for {}"
                            " with tenant_id {}".format(name, tenant_id))
                raise exceptions.AlreadyExistsException(
                    "An inhibit rule with the name {} already exists".format(
                        name))

            found_inhibit_rule_id = \
                inhibit_rules[0]['id']
            if found_inhibit_rule_id != expected_id:
                LOG.warning("Found existing inhibit rule for {} with tenant_id"
                            " {} with unexpected id {}".format(name, tenant_id,
                                                               found_inhibit_rule_id))
                raise exceptions.AlreadyExistsException(
                    "An inhibit rule with the name {} already exists with id"
                    " {}".format(name, found_inhibit_rule_id))

    def _send_inhibit_rule_created_event(self, tenant_id, inhibit_rule_id,
                                         name, expression):
        try:
            result_expression = aql_parser.RuleExpressionParser(str(expression)).parse()
            result_expression = result_expression[0].get_struct("inhibit")
        except Exception as ex:
            LOG.debug(ex)
            raise exception.HTTPUnprocessableEntityError('Unprocessable Entity', str(ex))
        inhibit_rule_created_event_msg = {
            u'inhibit-rule-created':
                {u'tenantId': tenant_id,
                 u'id': inhibit_rule_id,
                 u'name': name,
                 u'source_match': result_expression['source_match'],
                 u'target_match': result_expression['target_match'],
                 u'equal': result_expression['equal'],
                 u'exclusions': result_expression['exclusions']
                 }
        }
        self.send_rule_event(self.rule_updates_message_queue,
                             inhibit_rule_created_event_msg)


def get_query_inhibit_rule_description(inhibit_rule, return_none=False):
    if 'description' in inhibit_rule:
        return inhibit_rule['description']
    elif return_none:
        return None
    else:
        return constants.RULE_DESCRIPTION


def get_query_inhibit_rule_param(inhibit_rule, param, return_none=False):
    try:
        if param in inhibit_rule:
            param_value = inhibit_rule[param]
            return param_value
        elif return_none:
            return None
        else:
            raise Exception("Missing inhibit rule {}".format(param))
    except Exception as ex:
        LOG.debug(ex)
        raise exception.HTTPUnprocessableEntityError('Unprocessable Entity',
                                                     str(ex))


def get_comma_separated_str_as_list(comma_separated_str):
    if not comma_separated_str:
        return []
    else:
        return comma_separated_str.decode('utf8').split(',')
