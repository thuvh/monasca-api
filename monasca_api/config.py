# Copyright 2017 FUJITSU LIMITED
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
from oslo_log import log

from monasca_api import version

CONF = cfg.CONF
LOG = log.getLogger(__name__)

_CONF_LOADED = False


def parse_args(config_file=None,
               log_config_file=None):
    """Loads application configuration.

    Loads entire application configuration just once.
    Provides ability to override expected
    locations of:

    * main configuration file (with config_file)
    * logging configuration file (with log_config_file)

    :param config_file:
    :param log_config_file:
    :type config_file: basestring
    :type log_config_file: basestring

    """
    global _CONF_LOADED
    if _CONF_LOADED:
        LOG.debug('Configuration has been already loaded')
        return

    log.set_defaults()
    log.register_options(CONF)

    CONF(args=[],
         # NOTE(trebskit) this disables any oslo.cfg CLI
         # opts as gunicorn has some trouble with them
         # i.e. gunicorn's argparse clashes with the one
         # defined inside oslo.cfg
         prog='api',
         project='monasca',
         version=version.version_str,
         default_config_files=[config_file] if config_file else None,
         description='RESTful API for alarming in the cloud')

    if log_config_file:
        CONF.set_override('log_config_append', log_config_file)

    log.setup(CONF,
              product_name='monasca-api',
              version=version.version_str)

    _CONF_LOADED = True
