# Copyright 2014 IBM Corp.
# Copyright 2016-2017 FUJITSU LIMITED
# (C) Copyright 2016-2017 Hewlett Packard Enterprise Development LP
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

from oslo_config import cfg

_DEFAULT_NOTIF_PERIODS = [0, 60]
TWO_MINUTES = 2 * 60 * 1000
TWO_WEEKS = 2 * 7 * 24 * 60 * 60 * 1000

global_opts = [
    cfg.StrOpt('region', sample_default='RegionOne',
               help='''
Region that API is running in
'''),
    cfg.ListOpt('valid_notification_periods', default=_DEFAULT_NOTIF_PERIODS,
                item_type=int,
                help='''
Valid periods for notification methods
'''),
    cfg.BoolOpt('should_validate_metric_timestamp_range', default=False,
                help='''
Valid metric timestamps are in legal range
'''),
    cfg.IntOpt('metric_timestamp_seconds_in_future_to_reject', default=TWO_MINUTES,
               help='''
The number of seconds in the future where a metric becomes invalid
'''),
    cfg.IntOpt('metric_timestamp_seconds_in_past_to_reject', default=TWO_WEEKS,
               help='''
The number of seconds in the past where a metric becomes invalid
''')
]


def register_opts(conf):
    conf.register_opts(global_opts)


def list_opts():
    return 'DEFAULT', global_opts
