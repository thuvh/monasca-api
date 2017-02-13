# Copyright 2014-2017 Hewlett Packard Enterprise Development LP
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
from monasca_common.simport import simport
from oslo_config import cfg
from oslo_log import log

from monasca_api.common.exceptions import HTTPUnprocessableEntityError
from monasca_api.common.repositories import exceptions
from monasca_api.v2.common.schemas import alarm_update_schema as schema_alarm
from monasca_api.v3.common import alarming
from monasca_api.v3.common import auth
from monasca_api.v3.common import pagination
from monasca_api.v3.common import utils
from monasca_api.v3.common import validation

LOG = log.getLogger(__name__)

DEFAULT_AUTHORIZED_ROLES = cfg.CONF.security.default_authorized_roles
GET_ALARMS_AUTHORIZED_ROLES = (cfg.CONF.security.default_authorized_roles +
                               cfg.CONF.security.read_only_authorized_roles)


class Alarms(alarming.Alarming):
    def __init__(self):
        try:
            super(Alarms, self).__init__()
            self._region = cfg.CONF.region
            self._alarms_repo = simport.load(
                cfg.CONF.repositories.alarms_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    @utils.exception_translator
    @auth.Authorize(authorized_roles=DEFAULT_AUTHORIZED_ROLES)
    def on_put(self, req, res, alarm_id):

        alarm = utils.parse_http_json_body(req)
        schema_alarm.validate(alarm)

        # Validator makes state optional, so check it here
        utils.apply_default(alarm, 'state', required=True)
        utils.apply_default(alarm, 'lifecycle_state', required=True)
        utils.apply_default(alarm, 'link', required=True)

        self._alarm_update(req.project_id, alarm_id, alarm['state'],
                           alarm['lifecycle_state'], alarm['link'])

        result = self._alarm_show(req.uri, req.project_id, alarm_id)

        res.body = utils.dumps_json_utf8(result)
        res.status = falcon.HTTP_200

    @utils.exception_translator
    @auth.Authorize(authorized_roles=DEFAULT_AUTHORIZED_ROLES)
    def on_patch(self, req, res, alarm_id):

        alarm = utils.parse_http_json_body(req)
        schema_alarm.validate(alarm)

        old_alarm = self._alarms_repo.get_alarm(req.project_id, alarm_id)[0]

        # if a field is not present or is None, replace it with the old value
        if 'state' not in alarm or not alarm['state']:
            alarm['state'] = old_alarm['state']
        if 'lifecycle_state' not in alarm or alarm['lifecycle_state'] is None:
            alarm['lifecycle_state'] = old_alarm['lifecycle_state']
        if 'link' not in alarm or alarm['link'] is None:
            alarm['link'] = old_alarm['link']

        self._alarm_patch(req.project_id, alarm_id, alarm['state'],
                          alarm['lifecycle_state'], alarm['link'])

        result = self._alarm_show(req.uri, req.project_id, alarm_id)

        res.body = utils.dumps_json_utf8(result)
        res.status = falcon.HTTP_200

    @utils.exception_translator
    @auth.Authorize(authorized_roles=DEFAULT_AUTHORIZED_ROLES)
    def on_delete(self, req, res, alarm_id):

        self._alarm_delete(req.project_id, alarm_id)
        res.status = falcon.HTTP_204

    @utils.exception_translator
    @auth.Authorize(authorized_roles=GET_ALARMS_AUTHORIZED_ROLES)
    def on_get(self, req, res, alarm_id=None):
        if alarm_id is None:
            query_params = {}
            req.get_param('state', store=query_params)
            req.get_param('severity', store=query_params)
            req.get_param_as_dimensions('metric_dimensions', store=query_params)
            req.get_param_as_list('sort_by', store=query_params, default=[])
            offset = req.get_param_as_int('offset')

            if 'state'in query_params and query_params['state'] is not None:
                validation.validate_alarm_state(query_params['state'])
                query_params['state'] = query_params['state'].upper()

            if 'severity' in query_params and query_params['severity'] is not None:
                validation.validate_severity_query(query_params['severity'])
                query_params['severity'] = query_params['severity'].upper()

            allowed_sort_by = {'alarm_id', 'alarm_definition_id', 'alarm_definition_name',
                               'state', 'severity', 'lifecycle_state', 'link',
                               'state_updated_timestamp', 'updated_timestamp', 'created_timestamp'}
            validation.validate_sort_by(query_params['sort_by'], allowed_sort_by)

            # ensure metric_dimensions is a list
            validation.validate_dimensions(query_params['metric_dimensions'])

            result = self._alarm_list(req.uri, req.tenant_id,
                                      query_params, offset,
                                      req.limit)

            res.body = utils.dumps_json_utf8(result)
            res.status = falcon.HTTP_200

        else:
            result = self._alarm_show(req.uri, req.tenant_id, alarm_id)

            res.body = utils.dumps_json_utf8(result)
            res.status = falcon.HTTP_200

    def _alarm_update(self, tenant_id, alarm_id, new_state, lifecycle_state,
                      link):

        alarm_metric_rows = self._alarms_repo.get_alarm_metrics(alarm_id)
        sub_alarm_rows = self._alarms_repo.get_sub_alarms(tenant_id, alarm_id)

        old_alarm, time_ms = self._alarms_repo.update_alarm(tenant_id, alarm_id,
                                                            new_state,
                                                            lifecycle_state, link)
        old_state = old_alarm['state']
        # alarm_definition_id is the same for all rows.
        alarm_definition_id = sub_alarm_rows[0]['alarm_definition_id']

        state_info = {u'alarmState': new_state, u'oldAlarmState': old_state}

        self._send_alarm_event(u'alarm-updated', tenant_id,
                               alarm_definition_id, alarm_metric_rows,
                               sub_alarm_rows, link, lifecycle_state, state_info)

        if old_state != new_state:
            try:
                alarm_definition_row = self._alarms_repo.get_alarm_definition(
                    tenant_id, alarm_id)
            except exceptions.DoesNotExistException:
                # Alarm definition does not exist. May have been deleted
                # in another transaction. In that case, all associated
                # alarms were also deleted, so don't send transition events.
                pass
            else:
                self._send_alarm_transitioned_event(tenant_id, alarm_id,
                                                    alarm_definition_row,
                                                    alarm_metric_rows,
                                                    old_state, new_state,
                                                    link, lifecycle_state,
                                                    time_ms)

    def _alarm_patch(self, tenant_id, alarm_id, new_state, lifecycle_state,
                     link):

        alarm_metric_rows = self._alarms_repo.get_alarm_metrics(alarm_id)
        sub_alarm_rows = self._alarms_repo.get_sub_alarms(tenant_id, alarm_id)

        old_alarm, time_ms = self._alarms_repo.update_alarm(tenant_id, alarm_id,
                                                            new_state,
                                                            lifecycle_state, link)

        # alarm_definition_id is the same for all rows.
        alarm_definition_id = sub_alarm_rows[0]['alarm_definition_id']

        state_info = {u'alarmState': new_state, u'oldAlarmState': old_alarm['state']}

        self._send_alarm_event(u'alarm-updated', tenant_id,
                               alarm_definition_id, alarm_metric_rows,
                               sub_alarm_rows, link, lifecycle_state, state_info)

        if old_alarm['state'] != new_state:
            try:
                alarm_definition_row = self._alarms_repo.get_alarm_definition(
                    tenant_id, alarm_id)
            except exceptions.DoesNotExistException:
                # Alarm definition does not exist. May have been deleted
                # in another transaction. In that case, all associated
                # alarms were also deleted, so don't send transition events.
                pass
            else:
                self._send_alarm_transitioned_event(tenant_id, alarm_id,
                                                    alarm_definition_row,
                                                    alarm_metric_rows,
                                                    old_alarm['state'], new_state,
                                                    link, lifecycle_state,
                                                    time_ms)

    def _alarm_delete(self, tenant_id, id):

        alarm_metric_rows = self._alarms_repo.get_alarm_metrics(id)
        sub_alarm_rows = self._alarms_repo.get_sub_alarms(tenant_id, id)

        self._alarms_repo.delete_alarm(tenant_id, id)

        # alarm_definition_id is the same for all rows.
        alarm_definition_id = sub_alarm_rows[0]['alarm_definition_id']

        self._send_alarm_event(u'alarm-deleted', tenant_id,
                               alarm_definition_id, alarm_metric_rows,
                               sub_alarm_rows, None, None)

    def _alarm_show(self, req_uri, tenant_id, alarm_id):

        alarm_rows = self._alarms_repo.get_alarm(tenant_id, alarm_id)

        req_uri_no_id = req_uri.replace('/' + alarm_id, "")
        first_row = True
        for alarm_row in alarm_rows:
            if first_row:
                ad = {u'id': alarm_row['alarm_definition_id'],
                      u'name': alarm_row['alarm_definition_name'],
                      u'severity': alarm_row['severity'], }
                pagination.add_links_to_resource(ad,
                                              re.sub('alarms',
                                                     'alarm-definitions',
                                                     req_uri_no_id))

                metrics = []
                alarm = {u'id': alarm_row['alarm_id'], u'metrics': metrics,
                         u'state': alarm_row['state'],
                         u'lifecycle_state': alarm_row['lifecycle_state'],
                         u'link': alarm_row['link'],
                         u'state_updated_timestamp':
                             alarm_row['state_updated_timestamp'].isoformat() +
                             'Z',
                         u'updated_timestamp':
                             alarm_row['updated_timestamp'].isoformat() + 'Z',
                         u'created_timestamp':
                             alarm_row['created_timestamp'].isoformat() + 'Z',
                         u'alarm_definition': ad}
                pagination.add_links_to_resource(alarm, req_uri_no_id)

                first_row = False

            dimensions = {}
            metric = {u'name': alarm_row['metric_name'],
                      u'dimensions': dimensions}

            if alarm_row['metric_dimensions']:
                for dimension in alarm_row['metric_dimensions'].split(','):
                    parsed_dimension = dimension.split('=')
                    dimensions[parsed_dimension[0]] = parsed_dimension[1]

            metrics.append(metric)

        return alarm

    def _alarm_list(self, req_uri, tenant_id, query_parms, offset, limit):

        alarm_rows = self._alarms_repo.get_alarms(tenant_id, query_parms,
                                                  offset, limit)

        result = []
        if not alarm_rows:
            return pagination.paginate_alarming(result, req_uri, limit)

        # Forward declaration
        alarm = {}
        prev_alarm_id = None
        for alarm_row in alarm_rows:
            if prev_alarm_id != alarm_row['alarm_id']:
                if prev_alarm_id is not None:
                    result.append(alarm)

                ad = {u'id': alarm_row['alarm_definition_id'],
                      u'name': alarm_row['alarm_definition_name'],
                      u'severity': alarm_row['severity'], }
                pagination.add_links_to_resource(ad,
                                              re.sub('alarms',
                                                     'alarm-definitions',
                                                     req_uri))

                metrics = []
                alarm = {u'id': alarm_row['alarm_id'], u'metrics': metrics,
                         u'state': alarm_row['state'],
                         u'lifecycle_state': alarm_row['lifecycle_state'],
                         u'link': alarm_row['link'],
                         u'state_updated_timestamp':
                             alarm_row['state_updated_timestamp'].isoformat() +
                             'Z',
                         u'updated_timestamp':
                             alarm_row['updated_timestamp'].isoformat() + 'Z',
                         u'created_timestamp':
                             alarm_row['created_timestamp'].isoformat() + 'Z',
                         u'alarm_definition': ad}
                pagination.add_links_to_resource(alarm, req_uri)

                prev_alarm_id = alarm_row['alarm_id']

            dimensions = {}
            metric = {u'name': alarm_row['metric_name'],
                      u'dimensions': dimensions}

            if alarm_row['metric_dimensions']:
                for dimension in alarm_row['metric_dimensions'].split(','):
                    parsed_dimension = dimension.split('=')
                    dimensions[parsed_dimension[0]] = parsed_dimension[1]

            metrics.append(metric)

        result.append(alarm)

        return pagination.paginate_alarming(result, req_uri, limit)


class AlarmsCount(alarming.Alarming):

    def __init__(self):
        try:
            super(AlarmsCount, self).__init__()
            self._region = cfg.CONF.region
            self._alarms_repo = simport.load(
                cfg.CONF.repositories.alarms_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    @utils.exception_translator
    @auth.Authorize(authorized_roles=GET_ALARMS_AUTHORIZED_ROLES)
    def on_get(self, req, res):
        query_params = {}
        req.get_param('state', store=query_params)
        req.get_param('severity', store=query_params)
        req.get_param_as_dimensions('metric_dimensions', store=query_params)
        req.get_param_as_list('group_by', store=query_params, default=[])
        offset = req.get_param_as_int('offset')

        if query_params['state'] is not None:
            validation.validate_alarm_state(query_params['state'])
            query_params['state'] = query_params['state'].upper()

        if query_params['severity'] is not None:
            validation.validate_severity_query(query_params['severity'])
            query_params['severity'] = query_params['severity'].upper()

        self._validate_group_by(query_params['group_by'])
        validation.validate_dimensions(query_params['metric_dimensions'])

        result = self._alarms_count(req.uri, req.tenant_id, query_params, offset, req.limit)

        res.body = utils.dumps_json_utf8(result)
        res.status = falcon.HTTP_200

    def _alarms_count(self, req_uri, tenant_id, query_parms, offset, limit):

        count_data = self._alarms_repo.get_alarms_count(tenant_id, query_parms, offset, limit)

        # result = count_data
        result = {
            'links': [
                {
                    'rel': 'self',
                    'href': req_uri
                }
            ],
            'columns': ['count']
        }

        if len(count_data) == 0 or count_data[0]['count'] == 0:
            count = [0]
            if 'group_by' in query_parms:
                for field in query_parms['group_by']:
                    result['columns'].append(field)
                    count.append(None)
            result['counts'] = [count]
            return result

        if len(count_data) > limit:
            result['links'].append(
                {'rel': 'next',
                 'href': pagination.create_alarms_count_next_link(req_uri, offset, limit)})
            count_data = count_data[:limit]

        result['columns'].extend(query_parms['group_by'])

        result['counts'] = []
        for row in count_data:
            count_result = [row['count']]
            for field in query_parms['group_by']:
                count_result.append(row[field])
            result['counts'].append(count_result)

        return result

    def _validate_group_by(self, group_by):
        allowed_values = {'alarm_definition_id', 'name', 'state', 'severity',
                          'link', 'lifecycle_state', 'metric_name',
                          'dimension_name', 'dimension_value'}
        if not set(group_by).issubset(allowed_values):
            raise HTTPUnprocessableEntityError(
                "Unprocessable Entity",
                "One or more group-by values from {} are not in {}".format(group_by, allowed_values))


class AlarmsStateHistory(alarming.Alarming):
    def __init__(self):
        try:
            super(AlarmsStateHistory, self).__init__()
            self._region = cfg.CONF.region
            self._alarms_repo = simport.load(
                cfg.CONF.repositories.alarms_driver)()
            self._metrics_repo = simport.load(
                cfg.CONF.repositories.metrics_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    @utils.exception_translator
    @auth.Authorize(authorized_roles=GET_ALARMS_AUTHORIZED_ROLES)
    def on_get(self, req, res, alarm_id=None):

        if alarm_id is None:
            start_timestamp = req.get_param_as_datetime('start_time')
            end_timestamp = req.get_param_as_datetime('end_time')
            dimensions = req.get_param_as_dimensions('dimensions')
            offset = req.get_param('offset')

            validation.validate_dimensions(dimensions)
            validation.validate_time_range(start_timestamp, end_timestamp)

            result = self._alarm_history_list(req.tenant_id, start_timestamp,
                                              end_timestamp, dimensions,
                                              req.uri, offset, req.limit)

            res.body = utils.dumps_json_utf8(result)
            res.status = falcon.HTTP_200

        else:
            offset = req.get_param('offset')

            result = self._metrics_repo.alarm_history(req.tenant_id, alarm_id, offset,
                                                      req.limit)

            paginated_result = pagination.paginate(result, req.uri, req.limit)

            res.body = utils.dumps_json_utf8(paginated_result)
            res.status = falcon.HTTP_200

    def _alarm_history_list(self, tenant_id, start_timestamp,
                            end_timestamp, dimensions, req_uri, offset,
                            limit):

        # get_alarms expects 'metric_dimensions' for dimensions key.
        if dimensions is not None:
            new_query_parms = {'metric_dimensions': dimensions}
        else:
            new_query_parms = {}

        alarm_rows = self._alarms_repo.get_alarms(tenant_id, new_query_parms,
                                                  None, None)
        alarm_id_list = [alarm_row['alarm_id'] for alarm_row in alarm_rows]

        result = self._metrics_repo.alarm_history(tenant_id, alarm_id_list,
                                                  offset, limit,
                                                  start_timestamp,
                                                  end_timestamp)

        return pagination.paginate(result, req_uri, limit)
