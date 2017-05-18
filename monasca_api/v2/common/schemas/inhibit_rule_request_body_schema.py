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


inhibit_rule_schema = {
    voluptuous.Required('name'): voluptuous.All(
        voluptuous.Any(six.string_types[0]), voluptuous.Length(max=255)),
    voluptuous.Required('expression'): voluptuous.All(
        voluptuous.Any(six.string_types[0]), voluptuous.Length(max=1024)),
    voluptuous.Marker('description'): voluptuous.All(
        voluptuous.Any(six.string_types[0]), voluptuous.Length(max=255))}


def validate(msg, require_all=False):
    try:
        request_body_schema = voluptuous.Schema(inhibit_rule_schema,
                                                required=require_all,
                                                extra=True)
        request_body_schema(msg)
    except Exception as ex:
        LOG.debug(ex)
        raise exceptions.ValidationException(str(ex))
