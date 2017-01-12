# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
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

from oslo_log import log
from prometheus_client import Gauge
from prometheus_utils import SidecarBridge

LOG = log.getLogger(__name__)

SIDECAR_URL = os.environ.get('SIDECAR_URL', None)

RUNNING_WORKERS = Gauge('running_workers',
                        'The count of active worker processes',
                        ['_aggregate'])
RUNNING_WORKERS.labels('sum').set(1)


def init():
    LOG.debug('Initializing prometheus registry (pid %d)...', os.getpid())

    if SIDECAR_URL:
        bridge = SidecarBridge(SIDECAR_URL)
        bridge.start(10.0)
