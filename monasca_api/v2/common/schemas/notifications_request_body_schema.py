# (C) Copyright 2014-2016 Hewlett Packard Enterprise Development Company LP
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
from voluptuous import All
from voluptuous import Any
from voluptuous import Length
from voluptuous import Marker
from voluptuous import Required
from voluptuous import Schema

from monasca_api.v2.common.schemas import exceptions

LOG = log.getLogger(__name__)

schemes = ['http', 'https']

valid_periodic_intervals = [0, 1]

notification_schema = {
    Required('name'): Schema(All(Any(str, unicode), Length(max=250))),
    Required('type'): Schema(Any("EMAIL", "email", "WEBHOOK", "webhook", "PAGERDUTY", "pagerduty")),
    Required('address'): Schema(All(Any(str, unicode), Length(max=512))),
    Marker('periodic_interval'): All(Any(int, str))}

request_body_schema = Schema(Any(notification_schema))


def parse_and_validate(msg, require_all=False):
    try:
        request_body_schema(msg)
    except Exception as ex:
        LOG.debug(ex)
        raise exceptions.ValidationException(str(ex))

    if 'periodic_interval' not in msg:
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
        raise exceptions.ValidationException("Periodic Interval {} must be a valid integer".format(periodic_interval))
    if periodic_interval not in valid_periodic_intervals:
        raise exceptions.ValidationException("{} is not a valid periodic interval".format(periodic_interval))
    return periodic_interval
