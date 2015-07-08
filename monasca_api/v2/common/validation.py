# Copyright 2015 Hewlett-Packard
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

from oslo_log import log
import re

LOG = log.getLogger(__name__)

invalid_chars = "<>={}(),'\"\\\\;&"
restricted_chars = re.compile('[' + invalid_chars + ']')


def metric_name(name):
    assert isinstance(name, (str, unicode)), "Metric name must be a string"
    assert len(name) <= 255, "Metric name must be 255 characters or less"
    assert not restricted_chars.search(name), "Invalid characters in metric name " + name


def dimension_key(dkey):
    assert isinstance(dkey, (str, unicode)), "Dimension key must be a string"
    assert len(dkey) <= 255, "Dimension key must be 255 characters or less"
    assert not restricted_chars.search(dkey), "Invalid characters in dimension name " + dkey


def dimension_value(value):
    assert len(value) <= 255, "Dimension value must be 255 characters or less"
    assert not restricted_chars.search(value), "Invalid characters in dimension value " + value


def parse_and_validate_dimension_value(value):
    if not isinstance(value, (str, unicode)):
        str_value = str(value)
        LOG.warn("Converting dimension value to string '{}'".format(value))
    else:
        str_value = value
    dimension_value(str_value)
    return str_value