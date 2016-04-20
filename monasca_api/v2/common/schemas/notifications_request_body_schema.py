# Copyright 2014 Hewlett-Packard
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
import six.moves.urllib.parse as urlparse
from validate_email import validate_email
import voluptuous

from monasca_api.v2.common.schemas import exceptions

LOG = log.getLogger(__name__)

schemes = ['http', 'https']

valid_periodic_intervals = [0, 1]

notification_schema = {
    voluptuous.Required('name'): voluptuous.Schema(
        voluptuous.All(voluptuous.Any(str, unicode),
                       voluptuous.Length(max=250))),
    voluptuous.Required('type'): voluptuous.Schema(
        voluptuous.Any("EMAIL", "email", "WEBHOOK", "webhook",
                       "PAGERDUTY", "pagerduty")),
    voluptuous.Required('address'): voluptuous.Schema(
        voluptuous.All(voluptuous.Any(str, unicode),
                       voluptuous.Length(max=512)))}

request_body_schema = voluptuous.Schema(voluptuous.Any(notification_schema))


def parse_and_validate_notification(msg, require_all=False):
    try:
        request_body_schema(msg)
    except Exception as ex:
        LOG.debug(ex)
        raise exceptions.ValidationException(str(ex))

    if msg['periodic_interval'] is None:
        if require_all:
            raise exceptions.ValidationException("Periodic interval is required")
        else:
            msg['periodic_interval'] = 0
    else:
        msg['periodic_interval'] = _parse_and_validate_periodic_interval(msg['periodic_interval'])

    notification_type = str(msg['type']).upper()

    if notification_type == 'EMAIL':
        _validate_email(msg['address'])
    elif notification_type == 'WEBHOOK':
        _validate_url(msg['address'])

    if notification_type != 'WEBHOOK' and msg['periodic_interval'] != 0:
        raise exceptions.ValidationException("Periodic interval can only be set with webhooks")



def _validate_email(address):
    if not validate_email(address):
        raise exceptions.ValidationException("Address {} is not of correct format".format(address))


def _validate_url(address):
    try:
        parsed = urlparse.urlparse(address)
    except Exception:
        raise exceptions.ValidationException("Address {} is not of correct format".format(address))

    if not parsed.scheme:
        raise exceptions.ValidationException("Address {} does not have URL scheme".format(address))
    if not parsed.netloc:
        raise exceptions.ValidationException("Address {} does not have network location"
                                             .format(address))
    if parsed.scheme not in schemes:
        raise exceptions.ValidationException("Address {} scheme is not in {}"
                                             .format(address, schemes))


def _parse_and_validate_periodic_interval(periodic_interval):
    try:
        periodic_interval = int(periodic_interval)
    except Exception:
        raise Exception("Periodic Interval {} must be a valid integer", periodic_interval)
    if periodic_interval not in valid_periodic_intervals:
        raise Exception("{} is not a valid periodic interval", periodic_interval)
    return periodic_interval
