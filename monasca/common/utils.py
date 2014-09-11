# Copyright 2013 IBM Corp
#
# Author: Tong Li <litong01@us.ibm.com>
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

"""Miscellaneous utility functions for use with Monasca."""

import logging
import logging.handlers


def init_logging(conf):
    root = logging.getLogger()
    log_level = conf.get('log_level', 'ERROR').upper()
    if log_level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
        root.setLevel(log_level)
    else:
        root.setLevel('ERROR')

    log_file = (conf.get('log_dir', '/var/log/') +
                conf.get('log_file', 'monasca.log'))

    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=(1048576 * 5), backupCount=7, encoding='utf8')

    formatter = logging.Formatter('%(asctime)s %(name)s ' +
                                  '%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)


def conf_val(conf, name, default_value):
    val = conf.get(name, None)
    if val:
        if val.lower() == 'true':
            return True
        elif val.lower() == 'false':
            return False
        else:
            try:
                return int(val)
            except ValueError:
                try:
                    return float(val)
                except ValueError:
                    return val
    else:
        return default_value