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

from oslo_log import log
import six
import voluptuous

from monasca_api.v2.common.schemas import exceptions

LOG = log.getLogger(__name__)

MAX_ITEM_LENGTH = 50


def validate_action_list(notification_ids, action_state):
    if not isinstance(notification_ids, list):
        raise voluptuous.Invalid('Not a list: {}'.format(type(notification_ids)))
    existing = []
    for notification_id in notification_ids:
        if not isinstance(notification_id, six.string_types):
            raise voluptuous.Invalid('list item <{}> -> {} not one of (str, '
                                     'unicode)'.format(notification_id,
                                                       type(notification_id)))
        if len(notification_id) > MAX_ITEM_LENGTH:
            raise voluptuous.Invalid('length {} > {}'.format(
                len(notification_id), MAX_ITEM_LENGTH))
        if notification_id in existing:
            raise voluptuous.Invalid('Duplicate {} notification method {}'
                                     .format(action_state, notification_id))
        existing.append(notification_id)


def validate_ok_action_list(v):
    validate_action_list(v, 'OK')


def validate_alarm_action_list(v):
    validate_action_list(v, 'ALARM')


def validate_undetermined_action_list(v):
    validate_action_list(v, 'UNDETERMINED')


group_rule_schema = {
    voluptuous.Required('name'): voluptuous.All(
        voluptuous.Any(six.string_types[0]), voluptuous.Length(max=255)),
    voluptuous.Required('expression'): voluptuous.All(
        voluptuous.Any(six.string_types[0]), voluptuous.Length(max=1024)),
    voluptuous.Marker('description'): voluptuous.All(
        voluptuous.Any(six.string_types[0]), voluptuous.Length(max=255)),
    voluptuous.Marker('group_wait'): voluptuous.Any(six.string_types[0]),
    voluptuous.Marker('repeat_interval'): voluptuous.Any(six.string_types[0]),
    voluptuous.Marker('ok_actions'): validate_ok_action_list,
    voluptuous.Marker('alarm_actions'): validate_alarm_action_list,
    voluptuous.Marker('undetermined_actions'):
        validate_undetermined_action_list}


def validate(msg, require_all=False):
    try:
        request_body_schema = voluptuous.Schema(group_rule_schema,
                                                required=require_all,
                                                extra=True)
        request_body_schema(msg)
    except Exception as ex:
        LOG.debug(ex)
        raise exceptions.ValidationException(str(ex))
