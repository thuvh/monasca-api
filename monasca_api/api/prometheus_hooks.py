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

import glob
import os


def handle_server_starting(server):
    """A gunicorn hook to clean old prometheus data.

    This hook should be called for `on_starting` lifecycle events, before any
    workers have been initialized.

    :param server: the gunicorn server instance
    """
    if 'prometheus_multiproc_dir' not in os.environ:
        server.log.debug('`prometheus_multiproc_dir` not configured, '
                         'will skip worker data cleanup')
        return

    dir = os.environ['prometheus_multiproc_dir']
    matches = glob.glob(os.path.join(dir, '*.db'))

    server.log.debug('Clearing %d existing worker files...', len(matches))
    for match in matches:
        os.remove(match)


def handle_worker_exit(server, worker):
    if 'prometheus_multiproc_dir' not in os.environ:
        return

    server.log.info('Cleaning up exiting working: %d', worker.pid)
    from prometheus_client import multiprocess
    multiprocess.mark_process_dead(worker.pid)
