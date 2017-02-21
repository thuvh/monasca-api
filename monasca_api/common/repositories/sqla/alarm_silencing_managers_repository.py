# Copyright 2017 Hewlett Packard Enterprise Development LP
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

import datetime

from oslo_log import log
from oslo_utils import uuidutils

from monasca_api.common.repositories import \
    alarm_silencing_managers_repository as asmr
from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories.sqla import models
from monasca_api.common.repositories.sqla import sql_repository
from sqlalchemy import MetaData, insert, update
from sqlalchemy import select, bindparam, null

LOG = log.getLogger(__name__)


class AlarmSilencingManagersRepository(sql_repository.SQLRepository,
                                       asmr.AlarmSilencingManagersRepository):
    def __init__(self):
        super(AlarmSilencingManagersRepository, self).__init__()

        metadata = MetaData()
        self.asm = models.create_asm_model(metadata)
        asm = self.asm
        asm_s = asm.alias('asm')
        self.asm_s = asm_s

        self.base_query = (select([asm_s.c.id,
                                   asm_s.c.name,
                                   asm_s.c.matchers,
                                   asm_s.c.start_time,
                                   asm_s.c.end_time]))

        self.insert_asm_query = \
            (insert(asm).values(id=bindparam('b_id'),
                                tenant_id=bindparam('b_tenant_id'),
                                name=bindparam('b_name'),
                                matchers=bindparam('b_matchers'),
                                start_time=bindparam('b_start_time'),
                                end_time=bindparam('b_end_time'),
                                created_at=bindparam('b_created_at'),
                                updated_at=bindparam('b_updated_at')))

        self.update_asm_query = (
            update(asm)
            .where(asm.c.tenant_id == bindparam('b_tenant_id'))
            .where(asm.c.id == bindparam('b_id')))

        self.soft_delete_asm_query = (update(asm).where(
            asm.c.tenant_id == bindparam('b_tenant_id'))
            .where(asm.c.id == bindparam('b_id'))
            .where(asm.c.deleted_at == null())
            .values(deleted_at=datetime.datetime.utcnow()))

    @sql_repository.sql_try_catch_block
    def create_alarm_silencing_manager(self, tenant_id, name, matchers,
                                       start_time, end_time):
        with self._db_engine.begin() as conn:

            now = datetime.datetime.utcnow()
            alarm_silencing_manager_id = uuidutils.generate_uuid()

            conn.execute(self.insert_asm_query,
                         b_id=alarm_silencing_manager_id,
                         b_tenant_id=tenant_id,
                         b_name=name.encode('utf8'),
                         b_matchers=",".join(matchers).encode('utf8'),
                         b_start_time=start_time.encode('utf8'),
                         b_end_time=end_time.encode('utf8'),
                         b_created_at=now,
                         b_updated_at=now)

            return alarm_silencing_manager_id

    @sql_repository.sql_try_catch_block
    def get_alarm_silencing_managers(self, tenant_id, name=None, offset=None,
                                     limit=1000):

        with self._db_engine.connect() as conn:
            asm = self.asm_s
            params = {'b_tenant_id': tenant_id}
            query = (self.base_query
                     .where(asm.c.tenant_id == bindparam('b_tenant_id'))
                     .where(asm.c.deleted_at == null()))
            if name:
                query = query.where(asm.c.name == bindparam('b_name'))
                params['b_name'] = name.encode('utf8')

            query = query.limit(bindparam('b_limit'))
            params['b_limit'] = limit + 1

            return [dict(row) for row in conn.execute(
                query, params).fetchall()]

    @sql_repository.sql_try_catch_block
    def get_alarm_silencing_manager(self, tenant_id, _id):
        with self._db_engine.connect() as conn:
            return self._get_alarm_silencing_manager(conn, tenant_id, _id)

    @sql_repository.sql_try_catch_block
    def update_or_patch_alarm_silencing_manager(
            self, tenant_id, alarm_silencing_manager_id, name, matchers,
            start_time, end_time, patch=False):

        with self._db_engine.begin() as conn:
            original_row = self._get_alarm_silencing_manager(
                conn, tenant_id, alarm_silencing_manager_id)

            # Get a common update time
            now = datetime.datetime.utcnow()

            if name is None:
                new_name = original_row['name']
            else:
                new_name = name.encode('utf8')

            if matchers is None:
                new_matchers = original_row['matchers']
            else:
                new_matchers = ",".join(matchers).encode('utf8')

            if start_time is None:
                if patch:
                    new_start_time = original_row['start_time']
                else:
                    new_start_time = now  # default to current time
            else:
                new_start_time = start_time.encode('utf8')

            if end_time is None:
                if patch:
                    new_end_time = original_row['end_time']
                else:
                    new_end_time = now  # default to current time
            else:
                new_end_time = end_time.encode('utf8')

            conn.execute(
                self.update_asm_query.values(
                    name=bindparam('b_name'),
                    matchers=bindparam('b_matcheres'),
                    start_time=bindparam('b_start_time'),
                    end_time=bindparam('b_end_time'),
                    updated_at=bindparam('b_updated_at')),
                b_name=new_name,
                b_matcheres=new_matchers,
                b_start_time=new_start_time,
                b_end_time=new_end_time,
                b_updated_at=now,
                b_tenant_id=tenant_id,
                b_id=alarm_silencing_manager_id)

            asm = self.asm_s
            query = (self.base_query
                     .where(asm.c.tenant_id == bindparam('b_tenant_id'))
                     .where(asm.c.id == bindparam('b_id'))
                     .where(asm.c.deleted_at == null()))

            updated_row = conn.execute(query,
                                       b_id=alarm_silencing_manager_id,
                                       b_tenant_id=tenant_id).fetchone()

            if updated_row is None:
                raise Exception("Failed to find current alarm "
                                "silencing manager")

            # Return the alarm silencing manager
            return updated_row

    @sql_repository.sql_try_catch_block
    def delete_alarm_silencing_manager(self, tenant_id,
                                       alarm_silencing_manager_id):
        """Soft delete the alarm silencing manager.
        """

        with self._db_engine.begin() as conn:
            cursor = conn.execute(self.soft_delete_asm_query,
                                  b_tenant_id=tenant_id,
                                  b_id=alarm_silencing_manager_id)

            if cursor.rowcount < 1:
                return False

            return True

    def _get_alarm_silencing_manager(self, conn, tenant_id, _id):
        asm = self.asm_s
        query = (self.base_query
                 .where(asm.c.tenant_id == bindparam('b_tenant_id'))
                 .where(asm.c.id == bindparam('b_id'))
                 .where(asm.c.deleted_at == null()))

        row = conn.execute(query,
                           b_tenant_id=tenant_id,
                           b_id=_id).fetchone()

        if row is not None:
            return dict(row)
        else:
            raise exceptions.DoesNotExistException
