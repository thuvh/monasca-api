# Copyright 2014 IBM Corp
# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development LP
# Copyright 2017 Fujitsu LIMITED
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

dispatcher_opts = [
    cfg.StrOpt('versions', default=None,
               help='Versions'),
    cfg.StrOpt('version_2_0', default=None,
               help='Version 2.0'),
    cfg.StrOpt('metrics', default=None,
               help='Metrics'),
    cfg.StrOpt('metrics_measurements', default=None,
               help='Metrics measurements'),
    cfg.StrOpt('metrics_statistics', default=None,
               help='Metrics statistics'),
    cfg.StrOpt('metrics_names', default=None,
               help='Metrics names'),
    cfg.StrOpt('alarm_definitions', default=None,
               help='Alarm definitions'),
    cfg.StrOpt('alarms', default=None,
               help='Alarms'),
    cfg.StrOpt('alarms_count', default=None,
               help='Alarms Count'),
    cfg.StrOpt('alarms_state_history', default=None,
               help='Alarms state history'),
    cfg.StrOpt('notification_methods', default=None,
               help='Notification methods'),
    cfg.StrOpt('dimension_values', default=None,
               help='Dimension values'),
    cfg.StrOpt('dimension_names', default=None,
               help='Dimension names'),
    cfg.StrOpt('notification_method_types', default=None,
               help='notification_method_types methods'),
    cfg.StrOpt('healthchecks', default=None,
               help='Health checks endpoint')
]

dispatcher_group = cfg.OptGroup(name='dispatcher', title='dispatcher')


def register_opts(conf):
    conf.register_group(dispatcher_group)
    conf.register_opts(dispatcher_opts, dispatcher_group)


def list_opts():
    return dispatcher_group, dispatcher_opts
