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

import re

import falcon
import pyparsing
from monasca_common.simport import simport
from monasca_common.validation import metrics as metric_validation
from oslo_config import cfg
from oslo_log import log

import monasca_api.expression_parser.alarm_expr_parser
from monasca_api.common.exceptions import HTTPUnprocessableEntityError
from monasca_api.common.repositories import exceptions
from monasca_api.v2.common.schemas import (
    alarm_definition_request_body_schema as schema_alarms)
from monasca_api.v3.common import alarming
from monasca_api.v3.common import auth
from monasca_api.v3.common import pagination
from monasca_api.v3.common import utils
from monasca_api.v3.common import validation

LOG = log.getLogger(__name__)

DEFAULT_AUTHORIZED_ROLES = cfg.CONF.security.default_authorized_roles
GET_ALARMDEFS_AUTHORIZED_ROLES = (cfg.CONF.security.default_authorized_roles +
                                  cfg.CONF.security.read_only_authorized_roles)


class AlarmDefinitions(alarming.Alarming):

    def __init__(self):
        try:
            super(AlarmDefinitions, self).__init__()
            self._region = cfg.CONF.region
            self._alarm_definitions_repo = simport.load(
                cfg.CONF.repositories.alarm_definitions_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    @utils.exception_translator
    @auth.Authorize(authorized_roles=DEFAULT_AUTHORIZED_ROLES)
    def on_post(self, req, res):
        alarm_definition = utils.parse_http_json_body(req)

        utils.apply_default(alarm_definition, 'name', required=True)
        utils.apply_default(alarm_definition, 'expression', required=True)
        utils.apply_default(alarm_definition, 'description', default='')
        utils.apply_default(alarm_definition, 'severity', default='LOW')
        utils.apply_default(alarm_definition, 'match_by', default=[])
        utils.apply_default(alarm_definition, 'alarm_actions', default=[])
        utils.apply_default(alarm_definition, 'ok_actions', default=[])
        utils.apply_default(alarm_definition, 'undetermined_actions', default=[])

        self._validate_alarm_definition(alarm_definition)

        result = self._alarm_definition_create(req.project_id,
                                               alarm_definition)

        pagination.add_links_to_resource(result, req.uri)
        res.body = utils.dumps_json_utf8(result)
        res.status = falcon.HTTP_201

    @utils.exception_translator
    @auth.Authorize(authorized_roles=GET_ALARMDEFS_AUTHORIZED_ROLES)
    def on_get(self, req, res, alarm_definition_id=None):
        if alarm_definition_id is None:
            name = req.get_param('name')
            dimensions = req.get_param_as_dimensions('dimensions')
            severity = req.get_param('severity')
            sort_by = req.get_param_as_list('sort_by')
            offset = req.get_param_as_int('offset')

            if sort_by is not None:
                allowed_sort_by = {'id', 'name', 'severity',
                                   'updated_at', 'created_at'}
                validation.validate_sort_by(sort_by, allowed_sort_by)

            if severity is not None:
                validation.validate_severity_query(severity)
                severity = severity.upper()

            result = self._alarm_definition_list(req.project_id, name,
                                                 dimensions, severity,
                                                 req.uri, sort_by,
                                                 offset, req.limit)

            res.body = utils.dumps_json_utf8(result)
            res.status = falcon.HTTP_200

        else:
            result = self._alarm_definition_show(req.project_id,
                                                 alarm_definition_id)
            pagination.add_links_to_resource(result,
                                             re.sub('/' + alarm_definition_id, '', req.uri))

            res.body = utils.dumps_json_utf8(result)
            res.status = falcon.HTTP_200

    @utils.exception_translator
    @auth.Authorize(authorized_roles=DEFAULT_AUTHORIZED_ROLES)
    def on_put(self, req, res, alarm_definition_id):

        alarm_definition = utils.parse_http_json_body(req)

        utils.apply_default(alarm_definition, 'name', required=True)
        utils.apply_default(alarm_definition, 'expression', required=True)
        utils.apply_default(alarm_definition, 'description', required=True)
        utils.apply_default(alarm_definition, 'severity', required=True)
        utils.apply_default(alarm_definition, 'match_by', required=True)
        utils.apply_default(alarm_definition, 'actions_enabled', required=True)
        utils.apply_default(alarm_definition, 'alarm_actions', required=True)
        utils.apply_default(alarm_definition, 'ok_actions', required=True)
        utils.apply_default(alarm_definition, 'undetermined_actions', required=True)

        self._validate_name_not_conflicting(req.tenant_id,
                                            alarm_definition['name'],
                                            alarm_definition_id)

        self._validate_alarm_definition(alarm_definition)

        result = self._alarm_definition_update_or_patch(req.project_id,
                                                        alarm_definition_id,
                                                        alarm_definition,
                                                        patch=False)

        pagination.add_links_to_resource(result, req.uri)
        res.body = utils.dumps_json_utf8(result)
        res.status = falcon.HTTP_200

    @utils.exception_translator
    @auth.Authorize(authorized_roles=DEFAULT_AUTHORIZED_ROLES)
    def on_patch(self, req, res, alarm_definition_id):

        alarm_definition = utils.parse_http_json_body(req)

        if 'name' in alarm_definition:
            self._validate_name_not_conflicting(req.tenant_id,
                                                alarm_definition['name'],
                                                alarm_definition_id)

        self._fill_previous_definition_data(req.tenant_id, alarm_definition_id, alarm_definition)

        result = self._alarm_definition_update_or_patch(req.project_id,
                                                        alarm_definition_id,
                                                        alarm_definition,
                                                        patch=True)

        pagination.add_links_to_resource(result, req.uri)
        res.body = utils.dumps_json_utf8(result)
        res.status = falcon.HTTP_200

    @utils.exception_translator
    @auth.Authorize(authorized_roles=DEFAULT_AUTHORIZED_ROLES)
    def on_delete(self, req, res, alarm_definition_id):
        self._alarm_definition_delete(req.project_id, alarm_definition_id)
        res.status = falcon.HTTP_204

    def _fill_previous_definition_data(self, tenant_id, alarm_definition_id, alarm_definition):
        old_definition = self._alarm_definitions_repo.get_alarm_definition(tenant_id=tenant_id,
                                                                           id=alarm_definition_id)
        for key, value in old_definition.items():
            if key not in alarm_definition:
                alarm_definition[key] = value

    def _validate_name_not_conflicting(self, tenant_id, name, expected_id=None):
        definitions = self._alarm_definitions_repo.get_alarm_definitions(tenant_id=tenant_id,
                                                                         name=name,
                                                                         dimensions=None,
                                                                         severity=None,
                                                                         sort_by=None,
                                                                         offset=None,
                                                                         limit=0)
        if definitions:
            if not expected_id:
                LOG.warning("Found existing definition for {} with tenant_id {}".format(name, tenant_id))
                raise exceptions.AlreadyExistsException("An alarm definition with the name {} already exists"
                                                        .format(name))

            found_definition_id = definitions[0]['id']
            if found_definition_id != expected_id:
                LOG.warning("Found existing alarm definition for {} with tenant_id {} with unexpected id {}"
                            .format(name, tenant_id, found_definition_id))
                raise exceptions.AlreadyExistsException(
                    "An alarm definition with the name {} already exists with id {}"
                    .format(name, found_definition_id))

    def _alarm_definition_show(self, tenant_id, id):

        alarm_definition_row = (
            self._alarm_definitions_repo.get_alarm_definition(tenant_id, id))

        return self._build_alarm_definition_show_result(alarm_definition_row)

    def _build_alarm_definition_show_result(self, alarm_definition_row):

        match_by = get_comma_separated_str_as_list(
            alarm_definition_row['match_by'])

        alarm_actions_list = get_comma_separated_str_as_list(
            alarm_definition_row['alarm_actions'])

        ok_actions_list = get_comma_separated_str_as_list(
            alarm_definition_row['ok_actions'])

        undetermined_actions_list = get_comma_separated_str_as_list(
            alarm_definition_row['undetermined_actions'])

        description = (alarm_definition_row['description']
                       if alarm_definition_row['description'] is not None else None)

        expression = alarm_definition_row['expression'].decode('utf8')
        is_deterministic = is_definition_deterministic(expression)

        result = {
            u'actions_enabled': alarm_definition_row['actions_enabled'] == 1,
            u'alarm_actions': alarm_actions_list,
            u'undetermined_actions': undetermined_actions_list,
            u'ok_actions': ok_actions_list,
            u'description': description,
            u'expression': expression,
            u'deterministic': is_deterministic,
            u'id': alarm_definition_row['id'].decode('utf8'),
            u'match_by': match_by,
            u'name': alarm_definition_row['name'].decode('utf8'),
            u'severity': alarm_definition_row['severity'].decode(
                'utf8').upper()}

        return result

    def _alarm_definition_delete(self, tenant_id, id):

        sub_alarm_definition_rows = (
            self._alarm_definitions_repo.get_sub_alarm_definitions(id))
        alarm_metric_rows = self._alarm_definitions_repo.get_alarm_metrics(
            tenant_id, id)
        sub_alarm_rows = self._alarm_definitions_repo.get_sub_alarms(
            tenant_id, id)

        if not self._alarm_definitions_repo.delete_alarm_definition(
                tenant_id, id):
            raise falcon.HTTPNotFound

        self._send_alarm_definition_deleted_event(id,
                                                  sub_alarm_definition_rows)

        self._send_alarm_event(u'alarm-deleted', tenant_id, id,
                               alarm_metric_rows, sub_alarm_rows, None, None)

    def _alarm_definition_list(self, tenant_id, name, dimensions, severity, req_uri, sort_by,
                               offset, limit):

        alarm_definition_rows = (
            self._alarm_definitions_repo.get_alarm_definitions(tenant_id, name,
                                                               dimensions, severity, sort_by,
                                                               offset, limit))

        # TODO(Ryan) move this formatting down to repo level
        result = []
        for alarm_definition_row in alarm_definition_rows:
            match_by = get_comma_separated_str_as_list(
                alarm_definition_row['match_by'])

            alarm_actions_list = get_comma_separated_str_as_list(
                alarm_definition_row['alarm_actions'])

            ok_actions_list = get_comma_separated_str_as_list(
                alarm_definition_row['ok_actions'])

            undetermined_actions_list = get_comma_separated_str_as_list(
                alarm_definition_row['undetermined_actions'])

            expression = alarm_definition_row['expression']
            is_deterministic = is_definition_deterministic(expression)
            ad = {u'id': alarm_definition_row['id'],
                  u'name': alarm_definition_row['name'],
                  u'description': alarm_definition_row['description'] if (
                      alarm_definition_row['description']) else u'',
                  u'expression': alarm_definition_row['expression'],
                  u'deterministic': is_deterministic,
                  u'match_by': match_by,
                  u'severity': alarm_definition_row['severity'].upper(),
                  u'actions_enabled':
                      alarm_definition_row['actions_enabled'] == 1,
                  u'alarm_actions': alarm_actions_list,
                  u'ok_actions': ok_actions_list,
                  u'undetermined_actions': undetermined_actions_list}

            pagination.add_links_to_resource(ad, req_uri)
            result.append(ad)

        result = pagination.paginate_alarming(result, req_uri, limit)

        return result

    def _validate_alarm_definition(self, alarm_definition):

        try:
            schema_alarms.validate(alarm_definition, require_all=True)
            if 'match_by' in alarm_definition:
                for name in alarm_definition['match_by']:
                    metric_validation.validate_dimension_key(name)

        except Exception as ex:
            LOG.debug(ex)
            raise HTTPUnprocessableEntityError('Unprocessable Entity', ex.message)

    def _alarm_definition_update_or_patch(self, tenant_id,
                                          definition_id,
                                          alarm_definition,
                                          patch):

        if alarm_definition['name']:
            self._validate_name_not_conflicting(tenant_id,
                                                alarm_definition['name'],
                                                expected_id=definition_id)

        if alarm_definition['expression']:
            sub_expr_list = parse_alarm_definition_expression(alarm_definition['expression'])
        else:
            sub_expr_list = None

        alarm_def_row, sub_alarm_def_dicts = (
            self._alarm_definitions_repo.update_or_patch_alarm_definition(
                tenant_id,
                definition_id,
                alarm_definition['name'],
                alarm_definition['expression'],
                sub_expr_list,
                alarm_definition['actions_enabled'],
                alarm_definition['description'],
                alarm_definition['alarm_actions'],
                alarm_definition['ok_actions'],
                alarm_definition['undetermined_actions'],
                alarm_definition['match_by'],
                alarm_definition['severity'],
                patch))

        old_sub_alarm_def_event_dict = (
            self._build_sub_alarm_def_update_dict(
                sub_alarm_def_dicts['old']))

        new_sub_alarm_def_event_dict = (
            self._build_sub_alarm_def_update_dict(sub_alarm_def_dicts[
                'new']))

        changed_sub_alarm_def_event_dict = (
            self._build_sub_alarm_def_update_dict(sub_alarm_def_dicts[
                'changed']))

        unchanged_sub_alarm_def_event_dict = (
            self._build_sub_alarm_def_update_dict(sub_alarm_def_dicts[
                'unchanged']))

        result = self._build_alarm_definition_show_result(alarm_def_row)
        # Not all of the passed in parameters will be set if this called
        # from on_patch vs on_update. The alarm-definition-updated event
        # MUST have all of the fields set so use the dict built from the
        # data returned from the database
        alarm_def_event_dict = (
            {u'tenantId': tenant_id,
             u'alarmDefinitionId': definition_id,
             u'alarmName': result['name'],
             u'alarmDescription': result['description'],
             u'alarmExpression': result['expression'],
             u'severity': result['severity'],
             u'matchBy': result['match_by'],
             u'alarmActionsEnabled': result['actions_enabled'],
             u'oldAlarmSubExpressions': old_sub_alarm_def_event_dict,
             u'changedSubExpressions': changed_sub_alarm_def_event_dict,
             u'unchangedSubExpressions': unchanged_sub_alarm_def_event_dict,
             u'newAlarmSubExpressions': new_sub_alarm_def_event_dict})

        alarm_definition_updated_event = (
            {u'alarm-definition-updated': alarm_def_event_dict})

        self.send_event(self.events_message_queue,
                        alarm_definition_updated_event)

        return result

    def _build_sub_alarm_def_update_dict(self, sub_alarm_def_dict):

        sub_alarm_def_update_dict = {}
        for id, sub_alarm_def in sub_alarm_def_dict.items():
            dimensions = {}
            for name, value in sub_alarm_def.dimensions.items():
                dimensions[u'uname'] = value
            sub_alarm_def_update_dict[sub_alarm_def.id] = {}
            sub_alarm_def_update_dict[sub_alarm_def.id][u'function'] = (
                sub_alarm_def.function)
            sub_alarm_def_update_dict[sub_alarm_def.id][
                u'metricDefinition'] = (
                {u'name': sub_alarm_def.metric_name,
                 u'dimensions': dimensions})
            sub_alarm_def_update_dict[sub_alarm_def.id][u'operator'] = (
                sub_alarm_def.operator)
            sub_alarm_def_update_dict[sub_alarm_def.id][u'threshold'] = (
                sub_alarm_def.threshold)
            sub_alarm_def_update_dict[sub_alarm_def.id][u'period'] = (
                sub_alarm_def.period)
            sub_alarm_def_update_dict[sub_alarm_def.id][u'periods'] = (
                sub_alarm_def.periods)
            sub_alarm_def_update_dict[sub_alarm_def.id][u'expression'] = (
                sub_alarm_def.expression)

        return sub_alarm_def_update_dict

    def _alarm_definition_create(self, tenant_id, alarm_definition):

        sub_expr_list = parse_alarm_definition_expression(alarm_definition['expression'])

        self._validate_name_not_conflicting(tenant_id, alarm_definition['name'])

        alarm_definition_id = (
            self._alarm_definitions_repo.
            create_alarm_definition(tenant_id,
                                    alarm_definition['name'],
                                    alarm_definition['expression'],
                                    sub_expr_list,
                                    alarm_definition['description'],
                                    alarm_definition['severity'],
                                    alarm_definition['match_by'],
                                    alarm_definition['alarm_actions'],
                                    alarm_definition['undetermined_actions'],
                                    alarm_definition['ok_actions']))

        self._send_alarm_definition_created_event(tenant_id,
                                                  alarm_definition_id,
                                                  alarm_definition['name'],
                                                  alarm_definition['expression'],
                                                  sub_expr_list,
                                                  alarm_definition['description'],
                                                  alarm_definition['match_by'])
        result = alarm_definition
        result['id'] = alarm_definition_id
        result['deterministic'] = is_definition_deterministic(alarm_definition['expression'])

        return result

    def _send_alarm_definition_deleted_event(self, alarm_definition_id,
                                             sub_alarm_definition_rows):

        sub_alarm_definition_deleted_event_msg = {}
        alarm_definition_deleted_event_msg = {u"alarm-definition-deleted": {
            u"alarmDefinitionId": alarm_definition_id,
            u'subAlarmMetricDefinitions':
                sub_alarm_definition_deleted_event_msg}}

        for sub_alarm_definition in sub_alarm_definition_rows:
            sub_alarm_definition_deleted_event_msg[
                sub_alarm_definition['id']] = {
                u'name': sub_alarm_definition['metric_name']}
            dimensions = {}
            sub_alarm_definition_deleted_event_msg[sub_alarm_definition['id']][
                u'dimensions'] = dimensions
            if sub_alarm_definition['dimensions']:
                for dimension in sub_alarm_definition['dimensions'].split(','):
                    parsed_dimension = dimension.split('=')
                    dimensions[parsed_dimension[0]] = parsed_dimension[1]

        self.send_event(self.events_message_queue,
                        alarm_definition_deleted_event_msg)

    def _send_alarm_definition_created_event(self, tenant_id,
                                             alarm_definition_id, name,
                                             expression, sub_expr_list,
                                             description, match_by):

        alarm_definition_created_event_msg = {
            u'alarm-definition-created': {u'tenantId': tenant_id,
                                          u'alarmDefinitionId':
                                              alarm_definition_id,
                                          u'alarmName': name,
                                          u'alarmDescription': description,
                                          u'alarmExpression': expression,
                                          u'matchBy': match_by}}

        sub_expr_event_msg = {}
        for sub_expr in sub_expr_list:
            sub_expr_event_msg[sub_expr.id] = {
                u'function': sub_expr.normalized_func}
            metric_definition = {u'name': sub_expr.normalized_metric_name}
            sub_expr_event_msg[sub_expr.id][
                u'metricDefinition'] = metric_definition
            dimensions = {}
            for dimension in sub_expr.dimensions_as_list:
                parsed_dimension = dimension.split("=")
                dimensions[parsed_dimension[0]] = parsed_dimension[1]
            metric_definition[u'dimensions'] = dimensions
            sub_expr_event_msg[sub_expr.id][
                u'operator'] = sub_expr.normalized_operator
            sub_expr_event_msg[sub_expr.id][u'threshold'] = sub_expr.threshold
            sub_expr_event_msg[sub_expr.id][u'period'] = sub_expr.period
            sub_expr_event_msg[sub_expr.id][u'periods'] = sub_expr.periods
            sub_expr_event_msg[sub_expr.id][
                u'expression'] = sub_expr.fmtd_sub_expr_str

        alarm_definition_created_event_msg[u'alarm-definition-created'][
            u'alarmSubExpressions'] = sub_expr_event_msg

        self.send_event(self.events_message_queue,
                        alarm_definition_created_event_msg)


def parse_alarm_definition_expression(expression):
    try:
        return (monasca_api.expression_parser.alarm_expr_parser.
                AlarmExprParser(expression).sub_expr_list)
    except (pyparsing.ParseException,
            pyparsing.ParseFatalException) as ex:
        LOG.exception(ex)
        title = "Invalid alarm expression".encode('utf8')
        msg = "Parser failed on expression '{}' at column {}: {}".format(
            expression.encode('utf8'), str(ex.column).encode('utf8'),
            ex.msg.encode('utf8'))
        raise HTTPUnprocessableEntityError(title, msg)


def get_comma_separated_str_as_list(comma_separated_str):
    if not comma_separated_str:
        return []
    else:
        return comma_separated_str.decode('utf8').split(',')


def is_definition_deterministic(expression):
    """Evaluates if found expression is deterministic or not.

    In order to do that expression is parsed into sub expressions.
    Each sub expression needs to be deterministic in order for
    entity expression to be such.

    Otherwise expression is non-deterministic.

    :param str expression: expression to be evaluated
    :return: true/false
    :rtype: bool
    """
    expr_parser = (monasca_api.expression_parser
                   .alarm_expr_parser.AlarmExprParser(expression))
    sub_expressions = expr_parser.sub_expr_list

    for sub_expr in sub_expressions:
        if not sub_expr.deterministic:
            return False

    return True
