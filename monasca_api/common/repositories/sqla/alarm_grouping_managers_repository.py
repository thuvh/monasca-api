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

from monasca_api.common.repositories import alarm_grouping_managers_repository\
    as adr
from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories.sqla import models
from monasca_api.common.repositories.sqla import sql_repository
from sqlalchemy import MetaData, insert, update, delete
from sqlalchemy import select, text, bindparam, null

LOG = log.getLogger(__name__)


class AlarmGroupingManagersRepository(sql_repository.SQLRepository,
                                      adr.AlarmGroupingManagersRepository):
    def __init__(self):
        super(AlarmGroupingManagersRepository, self).__init__()

        metadata = MetaData()
        self.agm_a = models.create_agma_model(metadata)
        self.agm = models.create_agm_model(metadata)
        self.agm_e = models.create_agme_model(metadata)
        self.nm = models.create_nm_model(metadata)

        agm_a = self.agm_a
        agm = self.agm
        agm_e = self.agm_e
        nm = self.nm
        agm_s = agm.alias('agm')
        self.agm_s = agm_s
        nm_s = nm.alias('nm')

        agma = (select([agm_a.c.alarm_grouping_manager_id,
                        models.group_concat([agm_a.c.action_id]).label(
                            'actions')])
                .select_from(agm_a)
                .group_by(agm_a.c.alarm_grouping_manager_id)
                .alias('agma'))

        agme_columns = [agm_e.c.exclusion_name + text("'='") + agm_e.c.value]

        agmeg = (select([agm_e.c.alarm_grouping_manager_id,
                        models.group_concat(agme_columns).label('exclusions')])
                 .select_from(agm_e)
                 .group_by(agm_e.c.alarm_grouping_manager_id).alias('agmeg'))

        self.base_query_from = (agm_s.outerjoin(
            agma, agma.c.alarm_grouping_manager_id == agm_s.c.id).outerjoin(
            agmeg, agmeg.c.alarm_grouping_manager_id == agm_s.c.id))

        self.base_query = (select([agm_s.c.id,
                                   agm_s.c.name,
                                   agm_s.c.matchers,
                                   agm_s.c.group_wait,
                                   agm_s.c.repeat_interval,
                                   agma.c.actions,
                                   agmeg.c.exclusions]))

        self.create_alarm_grouping_manager_insert_agm_query = \
            (insert(agm).values(id=bindparam('b_id'),
                                tenant_id=bindparam('b_tenant_id'),
                                name=bindparam('b_name'),
                                matchers=bindparam('b_matchers'),
                                group_wait=bindparam('b_group_wait'),
                                repeat_interval=bindparam('b_repeat_interval'),
                                created_at=bindparam('b_created_at'),
                                updated_at=bindparam('b_updated_at')))

        b_agm_id = bindparam('b_alarm_grouping_manager_id')
        self.create_alarm_grouping_manager_insert_agme_query = \
            (insert(agm_e).values(alarm_grouping_manager_id=b_agm_id,
                                  exclusion_name=bindparam('b_exclusion_name'),
                                  value=bindparam('b_value')))

        self.insert_agma_query = (insert(agm_a).values(
            alarm_grouping_manager_id=bindparam('b_alarm_grouping_manager_id'),
            action_id=bindparam('b_action_id')))

        self.select_nm_query = (select([nm_s.c.id])
                                .select_from(nm_s)
                                .where(nm_s.c.id == bindparam('b_id')))

        self.update_or_patch_alarm_grouping_manager_update_agm_query = (
            update(agm)
            .where(agm.c.tenant_id == bindparam('b_tenant_id'))
            .where(agm.c.id == bindparam('b_id')))

        self.delete_agma_query = (
            delete(agm_a)
            .where(agm_a.c.alarm_grouping_manager_id ==
                   bindparam('b_alarm_grouping_manager_id')))

        self.delete_agme_query = (
            delete(agm_e)
            .where(agm_e.c.alarm_grouping_manager_id ==
                   bindparam('b_alarm_grouping_manager_id')))

        self.soft_delete_agm_query = (update(agm).where(
            agm.c.tenant_id == bindparam('b_tenant_id'))
            .where(agm.c.id == bindparam('b_id'))
            .where(agm.c.deleted_at == null())
            .values(deleted_at=datetime.datetime.utcnow()))

    @sql_repository.sql_try_catch_block
    def create_alarm_grouping_manager(self, tenant_id, name, matchers,
                                      group_wait, repeat_interval, exclusions,
                                      actions):
        with self._db_engine.begin() as conn:

            now = datetime.datetime.utcnow()
            alarm_grouping_manager_id = uuidutils.generate_uuid()

            conn.execute(self.create_alarm_grouping_manager_insert_agm_query,
                         b_id=alarm_grouping_manager_id,
                         b_tenant_id=tenant_id,
                         b_name=name.encode('utf8'),
                         b_matchers=",".join(matchers).encode('utf8'),
                         b_group_wait=group_wait.encode('utf8'),
                         b_repeat_interval=repeat_interval.encode('utf8'),
                         b_created_at=now,
                         b_updated_at=now)

            self._insert_into_exclusions(conn, alarm_grouping_manager_id,
                                         exclusions)
            self._insert_into_actions(conn, alarm_grouping_manager_id, actions)
            return alarm_grouping_manager_id

    @sql_repository.sql_try_catch_block
    def get_alarm_grouping_managers(self, tenant_id, name=None, offset=None,
                                    limit=1000):

        with self._db_engine.connect() as conn:
            agm = self.agm_s
            query_from = self.base_query_from
            params = {'b_tenant_id': tenant_id}
            query = (self.base_query
                     .select_from(query_from)
                     .where(agm.c.tenant_id == bindparam('b_tenant_id'))
                     .where(agm.c.deleted_at == null()))
            if name:
                query = query.where(agm.c.name == bindparam('b_name'))
                params['b_name'] = name.encode('utf8')

            query = query.limit(bindparam('b_limit'))
            params['b_limit'] = limit + 1

            return [dict(row) for row in conn.execute(
                query, params).fetchall()]

    @sql_repository.sql_try_catch_block
    def get_alarm_grouping_manager(self, tenant_id, _id):
        with self._db_engine.connect() as conn:
            return self._get_alarm_grouping_manager(conn, tenant_id, _id)

    @sql_repository.sql_try_catch_block
    def update_or_patch_alarm_grouping_manager(
            self, tenant_id, alarm_grouping_manager_id, name, matchers,
            group_wait, repeat_interval, exclusions, actions, patch=False):

        with self._db_engine.begin() as conn:
            original_row = self._get_alarm_grouping_manager(
                conn, tenant_id, alarm_grouping_manager_id)

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

            if group_wait is None:
                if patch:
                    new_group_wait = original_row['group_wait']
                else:
                    new_group_wait = '30s'.encode('utf8')  # default
            else:
                new_group_wait = group_wait.encode('utf8')

            if repeat_interval is None:
                if patch:
                    new_repeat_interval = original_row['repeat_interval']
                else:
                    new_repeat_interval = '2h'.encode('utf8')  # default
            else:
                new_repeat_interval = repeat_interval.encode('utf8')

            conn.execute(
                self.update_or_patch_alarm_grouping_manager_update_agm_query
                .values(name=bindparam('b_name'),
                        matchers=bindparam('b_matcheres'),
                        group_wait=bindparam('b_group_wait'),
                        repeat_interval=bindparam('b_repeat_interval'),
                        updated_at=bindparam('b_updated_at')),
                b_name=new_name,
                b_matcheres=new_matchers,
                b_group_wait=new_group_wait,
                b_repeat_interval=new_repeat_interval,
                b_updated_at=now,
                b_tenant_id=tenant_id,
                b_id=alarm_grouping_manager_id)

            # Delete old actions
            if patch:
                if actions is not None:
                    self._delete_alarm_grouping_manager_actions(
                        conn, alarm_grouping_manager_id)
            else:
                conn.execute(
                    self.delete_agma_query,
                    b_alarm_grouping_manager_id=alarm_grouping_manager_id)

            # Insert new actions
            self._insert_into_actions(conn, alarm_grouping_manager_id, actions)

            # Delete old exclusions
            if patch:
                if exclusions is not None:
                    self._delete_alarm_grouping_manager_exclusions(
                        conn, alarm_grouping_manager_id)
            else:
                conn.execute(
                    self.delete_agme_query,
                    b_alarm_grouping_manager_id=alarm_grouping_manager_id)

            # Insert new exclusions
            self._insert_into_exclusions(conn, alarm_grouping_manager_id,
                                         exclusions)

            agm = self.agm_s
            query = (self.base_query
                     .select_from(self.base_query_from)
                     .where(agm.c.tenant_id == bindparam('b_tenant_id'))
                     .where(agm.c.id == bindparam('b_id'))
                     .where(agm.c.deleted_at == null()))

            updated_row = conn.execute(query,
                                       b_id=alarm_grouping_manager_id,
                                       b_tenant_id=tenant_id).fetchone()

            if updated_row is None:
                raise Exception("Failed to find current alarm "
                                "grouping manager")

            # Return the alarm grouping manager
            return updated_row

    @sql_repository.sql_try_catch_block
    def delete_alarm_grouping_manager(self, tenant_id,
                                      alarm_grouping_manager_id):
        """Soft delete the alarm grouping manager.
        """

        with self._db_engine.begin() as conn:
            cursor = conn.execute(self.soft_delete_agm_query,
                                  b_tenant_id=tenant_id,
                                  b_id=alarm_grouping_manager_id)

            if cursor.rowcount < 1:
                return False

            return True

    def _get_alarm_grouping_manager(self, conn, tenant_id, _id):
        agm = self.agm_s
        query = (self.base_query
                 .select_from(self.base_query_from)
                 .where(agm.c.tenant_id == bindparam('b_tenant_id'))
                 .where(agm.c.id == bindparam('b_id'))
                 .where(agm.c.deleted_at == null()))

        row = conn.execute(query,
                           b_tenant_id=tenant_id,
                           b_id=_id).fetchone()

        if row is not None:
            return dict(row)
        else:
            raise exceptions.DoesNotExistException

    def _insert_into_actions(self, conn, alarm_grouping_manager_id, actions):
        if actions is None:
            return

        for action in actions:
            row = conn.execute(self.select_nm_query,
                               b_id=action.encode('utf8')).fetchone()
            if row is None:
                raise exceptions.InvalidUpdateException(
                    "Non-existent notification id {} submitted".format(
                        action.encode('utf8')))
            conn.execute(self.insert_agma_query,
                         b_alarm_grouping_manager_id=alarm_grouping_manager_id,
                         b_action_id=action.encode('utf8'))

    def _insert_into_exclusions(self, conn, alarm_grouping_manager_id,
                                exclusions):
        if exclusions is None:
            return

        exclusions_list = [[key, value] for key, value in exclusions.items()]
        for exclusion in exclusions_list:
            query = self.create_alarm_grouping_manager_insert_agme_query
            exclusion_name = exclusion[0].encode('utf8')
            exclusion_value = exclusion[1].encode('utf8')
            conn.execute(query,
                         b_alarm_grouping_manager_id=alarm_grouping_manager_id,
                         b_exclusion_name=exclusion_name,
                         b_value=exclusion_value)

    def _delete_alarm_grouping_manager_actions(self, conn, _id):
        conn.execute(self.delete_agma_query,
                     b_alarm_grouping_manager_id=_id)

    def _delete_alarm_grouping_manager_exclusions(self, conn, _id):
        conn.execute(self.delete_agme_query,
                     b_alarm_grouping_manager_id=_id)
