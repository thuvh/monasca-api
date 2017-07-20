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

import sys

from oslo_config import cfg
from oslo_db import options as oslo_db_opts
from oslo_log import log

from monasca_api import version

CONF = cfg.CONF
LOG = log.getLogger(__name__)

_CONF_LOADED = False
_GUNICORN_MARKER = 'gunicorn'


def parse_args(argv=None):
    """Loads application configuration.

    Loads entire application configuration just once.

    """
    global _CONF_LOADED
    if _CONF_LOADED:
        LOG.debug('Configuration has been already loaded')
        return

    log.set_defaults()
    log.register_options(CONF)
    oslo_db_opts.set_defaults(CONF, connection='sqlite://',
                              max_pool_size=10, max_overflow=20,
                              pool_timeout=10)

    argv = (argv if argv is not None else sys.argv[1:])
    args = ([] if _is_running_under_gunicorn() else argv or [])
    config_file = _get_deprecated_config_file()

    CONF(args=args,
         prog='api',
         project='monasca',
         version=version.version_str,
         default_config_files=[config_file] if config_file else None,
         description='RESTful API for alarming in the cloud')

    log.setup(CONF,
              product_name='monasca-api',
              version=version.version_str)
    _backward_compatible_db_opt(CONF)

    _CONF_LOADED = True


def _backward_compatible_db_opt(conf):
    """Registers database.url configuration opt.

    oslo.db expects that connection string to the database
    will be placed under **database.connection**. But until
    Pike release, monasca-api supports also **database.url** for
    the sake of backward compatibility.

    Note:
        This method needs to be removed after Pike is released.

    """
    url_opt = cfg.StrOpt(name='url',
                         default=conf.database.connection,
                         required=False,
                         deprecated_for_removal=True,
                         deprecated_since='1.6.0',
                         deprecated_reason=(
                             'Please use database.connection option,'
                             'database.url is scheduled for removal '
                             'after Pike is released.')
                         )

    conf.register_opts([url_opt], group='database')
    conf.set_override(name='connection', group='database',
                      override=conf.database.url)


def _is_running_under_gunicorn():
    """Evaluates if api runs under gunicorn."""
    content = filter(lambda x: x != sys.executable and _GUNICORN_MARKER in x,
                     sys.argv or [])
    return len(list(content) if not isinstance(content, list) else content) > 0


def _get_deprecated_config_file():
    """Get deprecated config file.

    Responsible for keeping  backward compatibility with old name of
    the configuration file i.e. api-config.conf.
    New name is => api.conf as prog=api.

    Note:
        Old configuration file name did not follow a convention
        oslo_config expects.

    """
    old_files = cfg.find_config_files(project='monasca', prog='api-config')
    if old_files is not None and len(old_files) > 0:
        LOG.warning('Detected old location "/etc/monasca/api-config.conf" '
                    'of main configuration file')
        return old_files[0]
