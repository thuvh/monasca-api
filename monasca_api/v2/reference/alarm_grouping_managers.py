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

from monasca_api.api import alarm_grouping_managers_api_v2
from monasca_api.common.repositories import exceptions
from monasca_api.v2.common.exceptions import HTTPUnprocessableEntityError
from monasca_api.v2.common.schemas import (
    alarm_grouping_manager_request_body_schema as schema_grouping_manager)
from monasca_api.v2.reference import helpers
from monasca_api.v2.reference import resource

LOG = log.getLogger(__name__)


class AlarmGroupingManagers(alarm_grouping_managers_api_v2.
                            AlarmGroupingManagersV2API):

    def __init__(self):
        try:
            super(AlarmGroupingManagers, self).__init__()
            self._region = cfg.CONF.region
            self._default_authorized_roles = (
                cfg.CONF.security.default_authorized_roles)
            self._get_alarm_grouping_managers_authorized_roles = (
                cfg.CONF.security.default_authorized_roles +
                cfg.CONF.security.read_only_authorized_roles)
            self._alarm_grouping_managers_repo = simport.load(
                cfg.CONF.repositories.alarm_grouping_managers_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)

    def on_post(self, req, res):
        helpers.validate_authorization(req, self._default_authorized_roles)

        alarm_grouping_manager = helpers.read_json_msg_body(req)

        self._validate_alarm_grouping_manager(alarm_grouping_manager)

        name = get_query_alarm_grouping_manager_name(alarm_grouping_manager)
        matchers = get_query_alarm_grouping_manager_matchers(
            alarm_grouping_manager)
        group_wait = get_query_alarm_grouping_manager_group_wait(
            alarm_grouping_manager)
        repeat_interval = get_query_alarm_grouping_manager_repeat_interval(
            alarm_grouping_manager)
        exclusions = get_query_alarm_grouping_manager_exclusions(
            alarm_grouping_manager)
        actions = get_query_alarm_grouping_manager_actions(
            alarm_grouping_manager)

        result = self._alarm_grouping_manager_create(req.project_id,
                                                     name,
                                                     matchers,
                                                     group_wait,
                                                     repeat_interval,
                                                     exclusions,
                                                     actions)

        helpers.add_links_to_resource(result, req.uri)
        res.body = helpers.dumpit_utf8(result)
        res.status = falcon.HTTP_201

    @resource.resource_try_catch_block
    def on_get(self, req, res, alarm_grouping_manager_id=None):
        if alarm_grouping_manager_id is None:
            helpers.validate_authorization(
                req, self._get_alarm_grouping_managers_authorized_roles)
            name = helpers.get_query_name(req)
            matchers = helpers.get_query_param(req, "matchers",
                                               default_val=None)
            exclusions = helpers.get_query_param(req,
                                                 "exclusions",
                                                 default_val=None)
            # TODO:  ADD VALIDATION
            # if matchers is not None:
                # validation.validate_matchers_query()

            offset = helpers.get_query_param(req, 'offset')
            if offset is not None and not isinstance(offset, int):
                try:
                    offset = int(offset)
                except Exception:
                    raise HTTPUnprocessableEntityError(
                        'Unprocessable Entity, Offset value {} must be an '
                        'integer'.format(offset))

            result = self._alarm_grouping_manager_list(req.project_id, name,
                                                       matchers, exclusions,
                                                       req.uri, offset,
                                                       req.limit)

            res.body = helpers.dumpit_utf8(result)
            res.status = falcon.HTTP_200

        else:
            helpers.validate_authorization(
                req, self._get_alarm_grouping_managers_authorized_roles)

            result = self._alarm_grouping_manager_show(
                req.project_id, alarm_grouping_manager_id)

            helpers.add_links_to_resource(
                result, re.sub('/' + alarm_grouping_manager_id, '', req.uri))
            res.body = helpers.dumpit_utf8(result)
            res.status = falcon.HTTP_200

    def _validate_alarm_grouping_manager(self, alarm_grouping_manager,
                                         require_all=False):
        try:
            schema_grouping_manager.validate(alarm_grouping_manager,
                                             require_all=require_all)
        except Exception as ex:
            LOG.debug(ex)
            raise HTTPUnprocessableEntityError('Unprocessable Entity',
                                               ex.message)

    @resource.resource_try_catch_block
    def _alarm_grouping_manager_create(self, tenant_id, name, matchers,
                                       group_wait, repeat_interval,
                                       exclusions, actions):
        self._validate_name_not_conflicting(tenant_id, name)
        alarm_grouping_manager_id = (
            self._alarm_grouping_managers_repo
                .create_alarm_grouping_manager(tenant_id, name, matchers,
                                               group_wait, repeat_interval,
                                               exclusions, actions))
        # EVENTS
        # self._send_alarm_grouping_manager_created_event(
        #     tenant_id, alarm_grouping_manager_id, name, matchers, exclusions)

        result = (
            {u'actions': actions,
             u'repeat_interval': repeat_interval,
             u'group_wait': group_wait,
             u'exclusions': exclusions,
             u'matchers': matchers,
             u'id': alarm_grouping_manager_id,
             u'name': name})

        return result

    def _alarm_grouping_manager_show(self, tenant_id, grouping_manager_id):

        alarm_grouping_manager_row = (
            self._alarm_grouping_managers_repo.get_alarm_grouping_manager(
                tenant_id, grouping_manager_id))

        return self._build_alarm_grouping_manager_show_result(
            alarm_grouping_manager_row)

    def _build_alarm_grouping_manager_show_result(
            self, alarm_grouping_manager_row):

        matchers = get_comma_separated_str_as_list(
            alarm_grouping_manager_row['matchers'])

        actions_list = get_comma_separated_str_as_list(
            alarm_grouping_manager_row['actions'])

        exclusions = (alarm_grouping_manager_row['exclusions']
                      if alarm_grouping_manager_row['exclusions'] is not None
                      else None)
        group_wait = (alarm_grouping_manager_row['group_wait']
                      if alarm_grouping_manager_row['group_wait'] is not None
                      else '30s')
        repeat_interval = (alarm_grouping_manager_row['repeat_interval']
                           if alarm_grouping_manager_row[
                                  'repeat_interval'] is not None
                           else '2h')

        result = {
            u'actions': actions_list,
            u'matchers': matchers,
            u'exclusions': exclusions,
            u'id': alarm_grouping_manager_row['id'].decode('utf8'),
            u'name': alarm_grouping_manager_row['name'].decode('utf8'),
            u'group_wait': group_wait,
            u'repeat_interval': repeat_interval}

        return result

    def _alarm_grouping_manager_list(self, tenant_id, name, matchers,
                                     exclusions, req_uri, offset, limit):
        alarm_grouping_manager_rows = (
            self._alarm_grouping_managers_repo.get_alarm_grouping_managers(
                tenant_id, name, matchers, exclusions, offset, limit))
        result = []
        for alarm_grouping_manager_row in alarm_grouping_manager_rows:
            matchers = get_comma_separated_str_as_list(
                alarm_grouping_manager_row['matchers'])

            actions_list = get_comma_separated_str_as_list(
              alarm_grouping_manager_row['actions'])

            exclusions = alarm_grouping_manager_row['exclusions']

            agm = {u'id': alarm_grouping_manager_row['id'],
                   u'name': alarm_grouping_manager_row['name'],
                   u'matchers': matchers,
                   u'group_wait': alarm_grouping_manager_row['group_wait'] if (
                      alarm_grouping_manager_row['group_wait'])
                   else u'30s',
                   u'repeat_interval': alarm_grouping_manager_row[
                      'repeat_interval'] if (
                      alarm_grouping_manager_row['repeat_interval'])
                   else u'2h',
                   u'actions': actions_list,
                   u'exclusions': exclusions}

            helpers.add_links_to_resource(agm, req_uri)
            result.append(agm)
        return result

    def _validate_name_not_conflicting(self, tenant_id, name,
                                       expected_id=None):
        alarm_grouping_managers = self._alarm_grouping_managers_repo.\
            get_alarm_grouping_managers(tenant_id=tenant_id, name=name,
                                        matchers=None, exclusions=None,
                                        offset=None, limit=0)
        if alarm_grouping_managers:
            if not expected_id:
                LOG.warning("Found existing alarm grouping manager for {} "
                            "with tenant_id {}".format(name, tenant_id))
                raise exceptions.AlreadyExistsException(
                    "An alarm grouping manager with the name {} already exists"
                    .format(name))

            found_grouping_manager_id = alarm_grouping_managers[0]['id']
            if found_grouping_manager_id != expected_id:
                LOG.warning("Found existing alarm grouping manager for {} "
                            "with tenant_id {} with unexpected id {}".
                            format(name, tenant_id, found_grouping_manager_id))
                raise exceptions.AlreadyExistsException(
                    "An alarm grouping manager with the name {} already "
                    "exists with id {}".format(name,
                                               found_grouping_manager_id))

    # def _send_alarm_grouping_manager_created_event(self, tenant_id,
    #                                                alarm_grouping_manager_id,
    #                                                name, matchers,
    #       exclusions):
    #     alarm_grouping_manager_created_event_msg = {
    #         u'alarm-grouping-manager-created':
    #             {u'tenantId': tenant_id,
    #              u'alarmGroupingManagerId': alarm_grouping_manager_id,
    #              u'alarmGroupingManagerName': name,
    #              u'alarmGroupingManagerMatchers': matchers,
    #              u'alarmGroupingManagerExclusions': exclusions
    #              }
    #     }
    #     self.send_event(self.events_message_queue,
    #                     alarm_grouping_manager_created_event_msg)


def get_query_alarm_grouping_manager_name(alarm_grouping_manager,
                                          return_none=False):
    try:
        if 'name' in alarm_grouping_manager:
            name = alarm_grouping_manager['name']
            return name
        else:
            if return_none:
                return None
            else:
                raise Exception("Missing name")
    except Exception as ex:
        LOG.debug(ex)
        raise HTTPUnprocessableEntityError('Unprocessable Entity', ex.message)


def get_query_alarm_grouping_manager_matchers(alarm_grouping_manager,
                                              return_none=False):
    try:
        if 'matchers' in alarm_grouping_manager:
            matchers = alarm_grouping_manager['matchers']
            return matchers
        else:
            if return_none:
                return None
            else:
                raise Exception("Missing grouping matchers")
    except Exception as ex:
        LOG.debug(ex)
        raise HTTPUnprocessableEntityError('Unprocessable Entity', ex.message)


def get_query_alarm_grouping_manager_group_wait(alarm_grouping_manager,
                                                return_none=False):
    if 'group_wait' in alarm_grouping_manager:
        group_wait = alarm_grouping_manager['group_wait']
        return group_wait
    else:
        if return_none:
            return None
        else:
            return '30s'  # default to 30 seconds


def get_query_alarm_grouping_manager_repeat_interval(alarm_grouping_manager,
                                                     return_none=False):
    if 'repeat_interval' in alarm_grouping_manager:
        repeat_interval = alarm_grouping_manager['repeat_interval']
        return repeat_interval
    else:
        if return_none:
            return None
        else:
            return '2h'  # default to 2h


def get_query_alarm_grouping_manager_exclusions(alarm_grouping_manager,
                                                return_none=False):
    if 'exclusions' in alarm_grouping_manager:
        exclusions = alarm_grouping_manager['exclusions']
        return exclusions
    else:
        if return_none:
            return None
        else:
            return []


def get_query_alarm_grouping_manager_actions(alarm_grouping_manager,
                                             return_none=False):
    if 'actions' in alarm_grouping_manager:
        actions = alarm_grouping_manager['actions']
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
