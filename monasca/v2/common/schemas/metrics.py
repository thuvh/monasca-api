# Copyright 2014 Hewlett-Packard
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from voluptuous import Schema
from voluptuous import Required, Any, All, Length, Range
from monasca.openstack.common import log
from monasca.v2.common.schemas import exceptions

LOG = log.getLogger(__name__)

# TODO: Add regex to validate dimension names don't use any excluded characters.
metric_schema = {
    Required('name'): All(unicode, Length(max=64)),
    Required('dimensions'): {All(unicode, Length(max=255)): All(unicode, Length(max=255))},
    Required('timestamp'): All(int, Range(min=0)),
    Required('value'): Any(int, float)
}

request_body_schema = Schema(Any(metric_schema, [metric_schema]))


def validate(msg):
    try:
        request_body_schema(msg)
    except Exception as ex:
        LOG.debug(ex)
        raise exceptions.ValidationException(ex.msg)