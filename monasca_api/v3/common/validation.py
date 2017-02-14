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

import monasca_common.validation.metrics as metric_validation

from monasca_api.common import exceptions


VALID_ALARM_STATES = {'ALARM', 'OK', 'UNDETERMINED'}
VALID_ALARM_DEFINITION_SEVERITIES = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}


def validate_metric_name(name):
    if name is not None:
        try:
            metric_validation.validate_name(name)
        except Exception as e:
            raise falcon.HTTPBadRequest("Invalid name", str(e))


def validate_dimensions(dimensions):
    try:
        for key, value in dimensions.items():
            metric_validation.validate_dimension_key(key)
            if value != "":
                if '|' in value:
                    values = value.split('|')
                    for v in values:
                        metric_validation.validate_dimension_value(key, v)
                else:
                    metric_validation.validate_dimension_value(key, value)
    except Exception as e:
        raise falcon.HTTPBadRequest("Invalid dimensions", str(e))


def validate_time_range(start_time, end_time=None):
    if end_time:
        if not start_time < end_time:
            raise falcon.HTTPBadRequest('Invalid time range',
                                        'start_time must be before end_time')


def validate_statistics(statistics):
    statistics = [statistic.lower() for statistic in statistics]
    if not all(statistic in ['avg', 'min', 'max', 'count', 'sum'] for
               statistic in statistics):
        raise falcon.HTTPBadRequest("Invalid statistic",
                                    "Statistics must be one of [avg, min, max, count, sum]")


def validate_sort_by(sort_by_list, allowed_sort_by):
    for sort_by_field in sort_by_list:
        sort_by_values = sort_by_field.split()
        if len(sort_by_values) > 2:
            raise exceptions.HTTPUnprocessableEntityError(
                "Unprocessable Entity",
                "Invalid sort_by {}".format(sort_by_field))
        if sort_by_values[0] not in allowed_sort_by:
            raise exceptions.HTTPUnprocessableEntityError(
                "Unprocessable Entity",
                "sort_by field {} must be one of [{}]".format(sort_by_values[0],
                                                              ','.join(list(allowed_sort_by))))
        if len(sort_by_values) > 1 and sort_by_values[1] not in ['asc', 'desc']:
            raise exceptions.HTTPUnprocessableEntityError(
                "Unprocessable Entity",
                "sort_by value {} must be 'asc' or 'desc'".format(sort_by_values[1]))
