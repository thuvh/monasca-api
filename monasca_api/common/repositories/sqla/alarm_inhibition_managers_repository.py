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

from monasca_api.common.repositories import alarm_inhibition_managers_repository as aimr
from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories.sqla import models
from monasca_api.common.repositories.sqla import sql_repository
from sqlalchemy import MetaData, insert, update, delete
from sqlalchemy import select, text, bindparam, null

LOG = log.getLogger(__name__)


class AlarmInhibitionManagersRepository(sql_repository.SQLRepository,
                                        aimr.AlarmInhibitionManagersRepository):
    def __init__(self):
        super(AlarmInhibitionManagersRepository, self).__init__()

        metadata = MetaData()
        self.aim = models.create_aim_model(metadata)
        self.aim_sm = models.create_aimsm_model(metadata)
        self.aim_tm = models.create_aimtm_model(metadata)

        aim = self.aim
        aim_sm = self.aim_sm
        aim_tm = self.aim_tm
        aim_s = aim.alias('aim')
        self.aim_s = aim_s

        aimsm_columns = [aim_sm.c.source_name + text("'='") +
                         aim_sm.c.source_value]
        aimtm_columns = [aim_tm.c.target_name + text("'='") +
                         aim_tm.c.target_value]

        aimsmg = (select([aim_sm.c.alarm_inhibition_manager_id,
                          models.group_concat(aimsm_columns).label(
                             'source_match')])
                  .select_from(aim_sm)
                  .group_by(aim_sm.c.alarm_inhibition_manager_id).alias(
            'aimsmg'))

        aimtmg = (select([aim_tm.c.alarm_inhibition_manager_id,
                          models.group_concat(aimtm_columns).label(
                              'target_match')])
                  .select_from(aim_tm)
                  .group_by(aim_tm.c.alarm_inhibition_manager_id).alias(
            'aimtmg'))

        self.base_query_from = (aim_s.outerjoin(
            aimsmg, aimsmg.c.alarm_inhibition_manager_id ==
            aim_s.c.id).outerjoin(
            aimtmg, aimtmg.c.alarm_inhibition_manager_id ==
            aim_s.c.id))

        self.base_query = (select([aim_s.c.id,
                                   aim_s.c.name,
                                   aim_s.c.equal,
                                   aimsmg.c.source_match,
                                   aimtmg.c.target_match]))

        self.insert_aim_query = \
            (insert(aim).values(id=bindparam('b_id'),
                                tenant_id=bindparam('b_tenant_id'),
                                name=bindparam('b_name'),
                                equal=bindparam('b_equal'),
                                created_at=bindparam('b_created_at'),
                                updated_at=bindparam('b_updated_at')))

        b_aim_id = bindparam('b_alarm_inhibition_manager_id')
        self.insert_aimsm_query = \
            (insert(aim_sm).values(alarm_inhibition_manager_id=b_aim_id,
                                   source_name=bindparam('b_source_name'),
                                   source_value=bindparam('b_source_value')))

        self.insert_aimtm_query = \
            (insert(aim_tm).values(alarm_inhibition_manager_id=b_aim_id,
                                   target_name=bindparam('b_target_name'),
                                   target_value=bindparam('b_target_value')))

        self.update_or_patch_alarm_inhibition_manager_update_aim_query = (
            update(aim).where(aim.c.tenant_id == bindparam('b_tenant_id'))
                       .where(aim.c.id == bindparam('b_id')))

        self.delete_aimsm_query = (
            delete(aim_sm)
            .where(aim_sm.c.alarm_inhibition_manager_id == bindparam(
                'b_alarm_inhibition_manager_id')))

        self.delete_aimtm_query = (
            delete(aim_tm)
            .where(aim_tm.c.alarm_inhibition_manager_id == bindparam(
                'b_alarm_inhibition_manager_id')))

        self.soft_delete_aim_query = (update(aim).where(
            aim.c.tenant_id == bindparam('b_tenant_id'))
            .where(aim.c.id == bindparam('b_id'))
            .where(aim.c.deleted_at == null())
            .values(deleted_at=datetime.datetime.utcnow()))

    @sql_repository.sql_try_catch_block
    def create_alarm_inhibition_manager(self, tenant_id, name, equal,
                                        source_match, target_match):
        with self._db_engine.begin() as conn:
            now = datetime.datetime.utcnow()
            alarm_inhibition_manager_id = uuidutils.generate_uuid()

            LOG.warn("****** TEST alarm_id ={}".format(
                alarm_inhibition_manager_id))
            conn.execute(self.insert_aim_query,
                         b_id=alarm_inhibition_manager_id,
                         b_tenant_id=tenant_id,
                         b_name=name.encode('utf8'),
                         b_equal=",".join(equal).encode('utf8'),
                         b_created_at=now,
                         b_updated_at=now)

            self._insert_into_source_match(
                conn, alarm_inhibition_manager_id, source_match)

            self._insert_into_target_match(
                conn, alarm_inhibition_manager_id, target_match)

            return alarm_inhibition_manager_id

    @sql_repository.sql_try_catch_block
    def get_alarm_inhibition_managers(self, tenant_id, name=None, offset=None,
                                      limit=1000):
        with self._db_engine.connect() as conn:
            aim = self.aim_s
            query_from = self.base_query_from
            params = {'b_tenant_id': tenant_id}
            query = (self.base_query
                     .select_from(query_from)
                     .where(aim.c.tenant_id == bindparam('b_tenant_id'))
                     .where(aim.c.deleted_at == null()))
            if name:
                query = query.where(aim.c.name == bindparam('b_name'))
                params['b_name'] = name.encode('utf8')

            query = query.limit(bindparam('b_limit'))
            params['b_limit'] = limit + 1

            return [dict(row) for row in conn.execute(
                query, params).fetchall()]

    @sql_repository.sql_try_catch_block
    def get_alarm_inhibition_manager(self, tenant_id, _id):
        with self._db_engine.connect() as conn:
            return self._get_alarm_inhibition_manager(conn, tenant_id, _id)

    @sql_repository.sql_try_catch_block
    def update_or_patch_alarm_inhibition_manager(
            self, tenant_id, alarm_inhibition_manager_id, name,
            equal, source_match, target_match, patch=False):

        with self._db_engine.begin() as conn:
            original_row = self._get_alarm_inhibition_manager(
                conn, tenant_id, alarm_inhibition_manager_id)

            # Get a common update time
            now = datetime.datetime.utcnow()

            if name is None:
                new_name = original_row['name']
            else:
                new_name = name.encode('utf8')

            if equal is None:
                new_equal = original_row['equal']
            else:
                new_equal = ",".join(equal).encode('utf8')

            conn.execute(
                self.update_or_patch_alarm_inhibition_manager_update_aim_query
                    .values(name=bindparam('b_name'),
                            equal=bindparam('b_equal'),
                            updated_at=bindparam('b_updated_at')),
                b_name=new_name,
                b_equal=new_equal,
                b_updated_at=now,
                b_tenant_id=tenant_id,
                b_id=alarm_inhibition_manager_id)

            # Delete old source_match
            if patch:
                if source_match is not None:
                    self._delete_alarm_inhibition_manager_source_match(
                        conn, alarm_inhibition_manager_id)
            else:
                conn.execute(
                    self.delete_aimsm_query,
                    b_alarm_inhibition_manager_id=alarm_inhibition_manager_id)

            # Insert new source_match
            self._insert_into_source_match(conn, alarm_inhibition_manager_id,
                                           source_match)

            # Delete old target_match
            if patch:
                if target_match is not None:
                    self._delete_alarm_inhibition_manager_target_match(
                        conn, alarm_inhibition_manager_id)
            else:
                conn.execute(
                    self.delete_aimtm_query,
                    b_alarm_inhibition_manager_id=alarm_inhibition_manager_id)

            # Insert new target_match
            self._insert_into_target_match(conn, alarm_inhibition_manager_id,
                                           target_match)

            aim = self.aim_s
            query = (self.base_query
                     .select_from(self.base_query_from)
                     .where(aim.c.tenant_id == bindparam('b_tenant_id'))
                     .where(aim.c.id == bindparam('b_id'))
                     .where(aim.c.deleted_at == null()))

            updated_row = conn.execute(query,
                                       b_id=alarm_inhibition_manager_id,
                                       b_tenant_id=tenant_id).fetchone()

            if updated_row is None:
                raise Exception("Failed to find current alarm inhibition manager")

            # Return the alarm inhibition manager
            return updated_row

    @sql_repository.sql_try_catch_block
    def delete_alarm_inhibition_manager(self, tenant_id,
                                        alarm_inhibition_manager_id):
        """Soft delete the alarm inhibition manager.
        """

        with self._db_engine.begin() as conn:
            cursor = conn.execute(self.soft_delete_aim_query,
                                  b_tenant_id=tenant_id,
                                  b_id=alarm_inhibition_manager_id)

            if cursor.rowcount < 1:
                return False

            return True

    def _insert_into_source_match(
            self, conn, alarm_inhibition_manager_id, source_match):
        if source_match is None:
            return

        source_match_list = [[key, value] for key, value in
                             source_match.items()]
        for source_match in source_match_list:
            query = self.insert_aimsm_query
            source_name = source_match[0].encode('utf8')
            source_value = source_match[1].encode('utf8')
            conn.execute(
                query,
                b_alarm_inhibition_manager_id=alarm_inhibition_manager_id,
                b_source_name=source_name,
                b_source_value=source_value)

    def _insert_into_target_match(
            self, conn, alarm_inhibition_manager_id, target_match):
        if target_match is None:
            return

        target_match_list = [[key, value] for key, value in
                             target_match.items()]
        for target_match in target_match_list:
            query = self.insert_aimtm_query
            target_name = target_match[0].encode('utf8')
            target_value = target_match[1].encode('utf8')
            conn.execute(
                query,
                b_alarm_inhibition_manager_id=alarm_inhibition_manager_id,
                b_target_name=target_name,
                b_target_value=target_value)

    def _get_alarm_inhibition_manager(self, conn, tenant_id, _id):
        aim = self.aim_s
        query = (self.base_query
                 .select_from(self.base_query_from)
                 .where(aim.c.tenant_id == bindparam('b_tenant_id'))
                 .where(aim.c.id == bindparam('b_id'))
                 .where(aim.c.deleted_at == null()))

        row = conn.execute(query,
                           b_tenant_id=tenant_id,
                           b_id=_id).fetchone()

        if row is not None:
            return dict(row)
        else:
            raise exceptions.DoesNotExistException

    def _delete_alarm_inhibition_manager_source_match(self, conn, _id):
        conn.execute(self.delete_aimsm_query,
                     b_alarm_inhibition_manager_id=_id)

    def _delete_alarm_inhibition_manager_target_match(self, conn, _id):
        conn.execute(self.delete_aimtm_query,
                     b_alarm_inhibition_manager_id=_id)
