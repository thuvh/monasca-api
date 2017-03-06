# Copyright 2014 IBM Corp
# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development LP
# Copyright 2017 Fujitsu LIMITED
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

import os
from wsgiref import simple_server

import falcon
from monasca_common.simport import simport
from oslo_config import cfg
from oslo_log import log
import paste.deploy

from monasca_api.api.core import request
from monasca_api import version

dispatcher_opts = [cfg.StrOpt('versions', default=None,
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
                              help='notification_method_types methods')]

dispatcher_group = cfg.OptGroup(name='dispatcher', title='dispatcher')
cfg.CONF.register_group(dispatcher_group)
cfg.CONF.register_opts(dispatcher_opts, dispatcher_group)

LOG = log.getLogger(__name__)


def launch(args):

    log.set_defaults()
    log.register_options(cfg.CONF)

    cfg.CONF(args=args.get('oslo.args', []),
             # NOTE(trebskit) that effectively disables CLI args from oslo.*
             # args list build from code below is passed
             # instead of actual CLI arguments
             # reason for that is having gunicorn with different argparse that
             # clashes with oslo.cfg argparse
             prog='api',
             project='monasca',
             version=version.version_str,
             description='REST-ful API to collect metric')
    log.setup(cfg.CONF,
              product_name='monasca-log-api',
              version=version.version_str)

    app = falcon.API(request_type=request.Request)

    versions = simport.load(cfg.CONF.dispatcher.versions)()
    app.add_route("/", versions)
    app.add_route("/{version_id}", versions)

    # The following resource is a workaround for a regression in falcon 0.3
    # which causes the path '/v2.0' to not route to the versions resource
    version_2_0 = simport.load(cfg.CONF.dispatcher.version_2_0)()
    app.add_route("/v2.0", version_2_0)

    metrics = simport.load(cfg.CONF.dispatcher.metrics)()
    app.add_route("/v2.0/metrics", metrics)

    metrics_measurements = simport.load(
        cfg.CONF.dispatcher.metrics_measurements)()
    app.add_route("/v2.0/metrics/measurements", metrics_measurements)

    metrics_statistics = simport.load(cfg.CONF.dispatcher.metrics_statistics)()
    app.add_route("/v2.0/metrics/statistics", metrics_statistics)

    metrics_names = simport.load(cfg.CONF.dispatcher.metrics_names)()
    app.add_route("/v2.0/metrics/names", metrics_names)

    alarm_definitions = simport.load(cfg.CONF.dispatcher.alarm_definitions)()
    app.add_route("/v2.0/alarm-definitions/", alarm_definitions)
    app.add_route("/v2.0/alarm-definitions/{alarm_definition_id}",
                  alarm_definitions)

    alarms = simport.load(cfg.CONF.dispatcher.alarms)()
    app.add_route("/v2.0/alarms", alarms)
    app.add_route("/v2.0/alarms/{alarm_id}", alarms)

    alarm_count = simport.load(cfg.CONF.dispatcher.alarms_count)()
    app.add_route("/v2.0/alarms/count/", alarm_count)

    alarms_state_history = simport.load(
        cfg.CONF.dispatcher.alarms_state_history)()
    app.add_route("/v2.0/alarms/state-history", alarms_state_history)
    app.add_route("/v2.0/alarms/{alarm_id}/state-history",
                  alarms_state_history)

    notification_methods = simport.load(
        cfg.CONF.dispatcher.notification_methods)()
    app.add_route("/v2.0/notification-methods", notification_methods)
    app.add_route("/v2.0/notification-methods/{notification_method_id}",
                  notification_methods)

    dimension_values = simport.load(cfg.CONF.dispatcher.dimension_values)()
    app.add_route("/v2.0/metrics/dimensions/names/values", dimension_values)

    dimension_names = simport.load(cfg.CONF.dispatcher.dimension_names)()
    app.add_route("/v2.0/metrics/dimensions/names", dimension_names)

    notification_method_types = simport.load(
        cfg.CONF.dispatcher.notification_method_types)()
    app.add_route("/v2.0/notification-methods/types", notification_method_types)

    LOG.debug('Dispatcher drivers have been added to the routes!')
    return app


def get_wsgi_app(config_dir=None, **kwargs):
    if config_dir is None:
        config_dir = '/etc/monasca'

    oslo_args = ['--config-dir=%s' % config_dir]
    if 'log_config_append' in kwargs:
        oslo_args.append(('--log-config-append=%s'
                          % kwargs.get('log_config_append')))
    paste_file = kwargs.get('paste_file', 'api-paste.ini')

    LOG.debug('Initializing WSGI application using configuration from %s',
              config_dir)

    return (
        paste.deploy.loadapp(
                'config:%s' % paste_file,
                relative_to=config_dir,
                global_conf={
                    'oslo.args': oslo_args
                }
        )
    )


if __name__ == '__main__':
    conf_dir = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../../etc')

    wsgi_app = get_wsgi_app(
            config_dir=conf_dir,
            log_config_append=os.path.join(conf_dir, 'api-logging.conf')
    )
    httpd = simple_server.make_server('127.0.0.1', 8070, wsgi_app)
    httpd.serve_forever()
