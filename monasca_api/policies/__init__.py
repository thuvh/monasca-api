# Copyright 2017 FUJITSU LIMITED
# Copyright 2018 OP5 AB
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

import os
import pkgutil

from oslo_log import log
from oslo_utils import importutils

LOG = log.getLogger(__name__)
_BASE_MOD_PATH = 'monasca_api.policies.'

DEFAULT_ROLES = 'role:admin or ' \
                'role:domainuser or ' \
                'role:domainadmin or ' \
                'role:monasca-user'
READONLY_ROLES = 'role:monasca-read-only-user'
AGENT_ROLES = 'role:monasca-agent'
DELEGATE_ROLES = 'role:admin'


def load_policy_modules():
    """Load all modules that contain policies.

    Method iterates over modules of :py:mod:`monasca_events_api.policies`
    and imports only those that contain following methods:

    - list_rules

    """
    for modname in _list_module_names():
        mod = importutils.import_module(_BASE_MOD_PATH + modname)
        if hasattr(mod, 'list_rules'):
            yield mod


def _list_module_names():
    package_path = os.path.dirname(os.path.abspath(__file__))
    for _, modname, ispkg in pkgutil.iter_modules(path=[package_path]):
        if not (modname == "opts" and ispkg):
            yield modname


def list_rules():
    """List all policy modules rules.

    Goes through all policy modules and yields their rules

    """
    all_rules = []
    for mod in load_policy_modules():
        rules = mod.list_rules()
        all_rules.extend(rules)
    return all_rules
