# Copyright 2014 Hewlett-Packard
# Copyright 2016 FUJITSU LIMITED
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

from oslo_config import cfg
from oslo_log import log

from sqlalchemy import MetaData

from monasca_api.common.repositories import exceptions

LOG = log.getLogger(__name__)


class SQLRepository(object):

    def __init__(self):

        try:

            super(SQLRepository, self).__init__()

            self.conf = cfg.CONF
            url = None
            oslo_options = ["mysql_sql_mode", "idle_timeout", "max_pool_size",
                            "max_retries", "retry_interval", "max_overflow",
                            "pool_timeout"]
            engine_args = {}
            if self.conf.mysql.database_name is not None:
                settings_db = (self.conf.mysql.username,
                               self.conf.mysql.password,
                               self.conf.mysql.hostname,
                               self.conf.mysql.database_name)
                url = "mysql+pymysql://%s:%s@%s/%s" % settings_db
            else:
                database_conf = dict(self.conf.database)
                for option in oslo_options:
                    if option in database_conf:
                        engine_args[option] = database_conf.pop(option)
                if self.conf.database.url is not None:
                    url = self.conf.database.url
                else:
                    if 'url' in database_conf:
                        del database_conf['url']
                    url = str(URL(**database_conf))

            from oslo_db.sqlalchemy.engines import create_engine
            self._db_engine = create_engine(url, **engine_args)

            self.metadata = MetaData()

        except Exception as ex:
            LOG.exception(ex)
            raise exceptions.RepositoryException(ex)


def sql_try_catch_block(fun):
    def try_it(*args, **kwargs):

        try:

            return fun(*args, **kwargs)

        except exceptions.DoesNotExistException:
            raise
        except exceptions.InvalidUpdateException:
            raise
        except exceptions.AlreadyExistsException:
            raise
        except Exception as ex:
            LOG.exception(ex)
            raise
        # exceptions.RepositoryException(ex)

    return try_it
