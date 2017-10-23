# (C) Copyright 2017 Akira Yoshiyama <akirayoshiyama@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg

griddb_opts = [
    cfg.IPOpt('notification_address',
              help='Notification IP addresses of GridDB cluster',
              default='239.0.0.1'),
    cfg.PortOpt('notification_port',
                help='Notification port of GridDB cluster',
                default=31999),
    cfg.StrOpt('cluster_name',
               help='Name of GridDB cluster',
               default="mon"),
    cfg.StrOpt('user',
               help='User for GridDB cluster login'),
    cfg.StrOpt('password',
               secret=True,
               help='Password for GridDB cluster login'),
]

griddb_group = cfg.OptGroup(name='griddb')


def register_opts(conf):
    conf.register_group(griddb_group)
    conf.register_opts(griddb_opts, griddb_group)


def list_opts():
    return griddb_group, griddb_opts
