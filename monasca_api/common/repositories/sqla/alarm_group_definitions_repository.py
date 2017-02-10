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

from monasca_api.common.repositories import alarm_group_definitions_repository\
    as agdr
from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories.sqla import models
from monasca_api.common.repositories.sqla import sql_repository
from sqlalchemy import MetaData, insert, update, delete
from sqlalchemy import select, text, bindparam, null

LOG = log.getLogger(__name__)


class AlarmGroupDefinitionsRepository(sql_repository.SQLRepository,
                                      agdr.AlarmGroupDefinitionsRepository):
    def __init__(self):
        super(AlarmGroupDefinitionsRepository, self).__init__()

        metadata = MetaData()
        self.agd = models.create_agd_model(metadata)
        self.agd_a = models.create_agd_action_model(metadata)
        self.agd_e = models.create_agd_exclusion_model(metadata)
        self.nm = models.create_nm_model(metadata)

        agd_a = self.agd_a
        agd = self.agd
        agd_e = self.agd_e
        nm = self.nm
        agd_s = agd.alias('agd')
        self.agd_s = agd_s
        nm_s = nm.alias('nm')

        agd_aa = agd_a.alias('agd_aa')
        agd_action_a = (select([agd_aa.c.alarm_group_definition_id,
                        models.group_concat([agd_aa.c.action_id]).label(
                            'alarm_actions')])
                        .select_from(agd_aa)
                        .where(agd_aa.c.alarm_state == text("'ALARM'"))
                        .group_by(agd_aa.c.alarm_group_definition_id)
                        .alias('agd_action_a'))

        agd_ao = agd_a.alias('agd_ao')
        agd_action_o = (select([agd_ao.c.alarm_group_definition_id,
                                models.group_concat([agd_ao.c.action_id]).
                               label('ok_actions')])
                        .select_from(agd_ao)
                        .where(agd_ao.c.alarm_state == text("'OK'"))
                        .group_by(agd_ao.c.alarm_group_definition_id)
                        .alias('agd_action_o'))

        agd_au = agd_a.alias('agd_au')
        agd_action_u = (select([agd_au.c.alarm_group_definition_id,
                                models.group_concat([agd_au.c.action_id]).
                               label('undetermined_actions')])
                        .select_from(agd_au)
                        .where(agd_au.c.alarm_state == text("'UNDETERMINED'"))
                        .group_by(agd_au.c.alarm_group_definition_id)
                        .alias('agd_action_U'))

        agd_exclusion_columns = [agd_e.c.exclusion_name + text("'='") +
                                 agd_e.c.value]

        agd_exclusion = (select([agd_e.c.alarm_group_definition_id,
                         models.group_concat(agd_exclusion_columns).label('exclusions')])
                         .select_from(agd_e)
                         .group_by(agd_e.c.alarm_group_definition_id).alias(
            'agd_exclusion'))

        self.base_query_from = (
            agd_s.outerjoin(
                agd_action_a,
                agd_action_a.c.alarm_group_definition_id == agd_s.c.id)
            .outerjoin(
                agd_action_o,
                agd_action_o.c.alarm_group_definition_id == agd_s.c.id)
            .outerjoin(
                agd_action_u,
                agd_action_u.c.alarm_group_definition_id == agd_s.c.id)
            .outerjoin(
                agd_exclusion,
                agd_exclusion.c.alarm_group_definition_id == agd_s.c.id))

        self.base_query = (select([agd_s.c.id,
                                   agd_s.c.name,
                                   agd_s.c.matchers,
                                   agd_s.c.group_wait,
                                   agd_s.c.repeat_interval,
                                   agd_action_a.c.alarm_actions,
                                   agd_action_o.c.ok_actions,
                                   agd_action_u.c.undetermined_actions,
                                   agd_exclusion.c.exclusions]))

        self.insert_agd_query = \
            (insert(agd).values(id=bindparam('b_id'),
                                tenant_id=bindparam('b_tenant_id'),
                                name=bindparam('b_name'),
                                matchers=bindparam('b_matchers'),
                                group_wait=bindparam('b_group_wait'),
                                repeat_interval=bindparam('b_repeat_interval'),
                                created_at=bindparam('b_created_at'),
                                updated_at=bindparam('b_updated_at')))

        b_agd_id = bindparam('b_alarm_group_definition_id')
        self.insert_agd_exclusion_query = \
            (insert(agd_e).values(alarm_group_definition_id=b_agd_id,
                                  exclusion_name=bindparam('b_exclusion_name'),
                                  value=bindparam('b_value')))

        self.insert_agd_action_query = (insert(agd_a).values(
            alarm_group_definition_id=bindparam('b_alarm_group_definition_id'),
            alarm_state=bindparam('b_alarm_state'),
            action_id=bindparam('b_action_id')))

        self.select_nm_query = (select([nm_s.c.id])
                                .select_from(nm_s)
                                .where(nm_s.c.id == bindparam('b_id')))

        self.update_agd_query = (
            update(agd)
            .where(agd.c.tenant_id == bindparam('b_tenant_id'))
            .where(agd.c.id == bindparam('b_id')))

        self.delete_agd_action_query = (
            delete(agd_a)
            .where(agd_a.c.alarm_group_definition_id ==
                   bindparam('b_alarm_group_definition_id'))
            .where(agd_a.c.alarm_state == bindparam('b_alarm_state')))

        self.delete_agd_exclusion_query = (
            delete(agd_e)
            .where(agd_e.c.alarm_group_definition_id ==
                   bindparam('b_alarm_group_definition_id')))

        self.soft_delete_agd_query = (update(agd).where(
            agd.c.tenant_id == bindparam('b_tenant_id'))
            .where(agd.c.id == bindparam('b_id'))
            .where(agd.c.deleted_at == null())
            .values(deleted_at=datetime.datetime.utcnow()))

    @sql_repository.sql_try_catch_block
    def create_alarm_group_definition(self, tenant_id, name, matchers,
                                      group_wait, repeat_interval, exclusions,
                                      alarm_actions, ok_actions,
                                      undetermined_actions):
        with self._db_engine.begin() as conn:

            now = datetime.datetime.utcnow()
            alarm_group_definition_id = uuidutils.generate_uuid()

            conn.execute(self.insert_agd_query,
                         b_id=alarm_group_definition_id,
                         b_tenant_id=tenant_id,
                         b_name=name.encode('utf8'),
                         b_matchers=",".join(matchers).encode('utf8'),
                         b_group_wait=group_wait.encode('utf8'),
                         b_repeat_interval=repeat_interval.encode('utf8'),
                         b_created_at=now,
                         b_updated_at=now)

            self._insert_into_exclusions(conn, alarm_group_definition_id,
                                         exclusions)
            self._insert_into_actions(conn, alarm_group_definition_id,
                                      alarm_actions, u"ALARM")
            self._insert_into_actions(conn, alarm_group_definition_id,
                                      ok_actions, u"OK")
            self._insert_into_actions(conn, alarm_group_definition_id,
                                      undetermined_actions, u"UNDETERMINED")
            return alarm_group_definition_id

    @sql_repository.sql_try_catch_block
    def get_alarm_group_definitions(self, tenant_id, name=None, offset=None,
                                    limit=1000):

        with self._db_engine.connect() as conn:
            agd = self.agd_s
            query_from = self.base_query_from
            params = {'b_tenant_id': tenant_id}
            query = (self.base_query
                     .select_from(query_from)
                     .where(agd.c.tenant_id == bindparam('b_tenant_id'))
                     .where(agd.c.deleted_at == null()))
            if name:
                query = query.where(agd.c.name == bindparam('b_name'))
                params['b_name'] = name.encode('utf8')

            query = query.limit(bindparam('b_limit'))
            params['b_limit'] = limit + 1

            return [dict(row) for row in conn.execute(
                query, params).fetchall()]

    @sql_repository.sql_try_catch_block
    def get_alarm_group_definition(self, tenant_id, _id):
        with self._db_engine.connect() as conn:
            return self._get_alarm_group_definition(conn, tenant_id, _id)

    @sql_repository.sql_try_catch_block
    def update_or_patch_alarm_group_definition(
            self, tenant_id, alarm_group_definition_id, name, matchers,
            group_wait, repeat_interval, exclusions, alarm_actions, ok_actions,
            undetermined_actions, patch=False):

        with self._db_engine.begin() as conn:
            original_row = self._get_alarm_group_definition(
                conn, tenant_id, alarm_group_definition_id)

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
                self.update_agd_query.values(
                    name=bindparam('b_name'),
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
                b_id=alarm_group_definition_id)

            # Delete old actions
            if alarm_actions is not None:
                self._delete_alarm_group_definition_actions(
                    conn, alarm_group_definition_id, 'ALARM')
            if ok_actions is not None:
                self._delete_alarm_group_definition_actions(
                    conn, alarm_group_definition_id, 'OK')
            if undetermined_actions is not None:
                self._delete_alarm_group_definition_actions(
                    conn, alarm_group_definition_id, 'UNDETERMINED')

            # Insert new actions
            if alarm_actions is not None:
                self._insert_into_actions(conn,
                                          alarm_group_definition_id,
                                          alarm_actions,
                                          'ALARM')
            if ok_actions is not None:
                self._insert_into_actions(conn,
                                          alarm_group_definition_id,
                                          ok_actions,
                                          'OK')
            if undetermined_actions is not None:
                self._insert_into_actions(conn,
                                          alarm_group_definition_id,
                                          undetermined_actions,
                                          'UNDETERMINED')

            # Delete old exclusions
            if patch:
                if exclusions is not None:
                    self._delete_alarm_group_definition_exclusions(
                        conn, alarm_group_definition_id)
            else:
                conn.execute(
                    self.delete_agd_exclusion_query,
                    b_alarm_group_definition_id=alarm_group_definition_id)

            # Insert new exclusions
            self._insert_into_exclusions(conn, alarm_group_definition_id,
                                         exclusions)

            agd = self.agd_s
            query = (self.base_query
                     .select_from(self.base_query_from)
                     .where(agd.c.tenant_id == bindparam('b_tenant_id'))
                     .where(agd.c.id == bindparam('b_id'))
                     .where(agd.c.deleted_at == null()))

            updated_row = conn.execute(query,
                                       b_id=alarm_group_definition_id,
                                       b_tenant_id=tenant_id).fetchone()

            if updated_row is None:
                raise Exception("Failed to find current alarm "
                                "group definition")

            # Return the alarm group definition
            return updated_row

    @sql_repository.sql_try_catch_block
    def delete_alarm_group_definition(self, tenant_id,
                                      alarm_group_definition_id):
        """Soft delete the alarm group definition.
        """

        with self._db_engine.begin() as conn:
            cursor = conn.execute(self.soft_delete_agd_query,
                                  b_tenant_id=tenant_id,
                                  b_id=alarm_group_definition_id)

            if cursor.rowcount < 1:
                return False

            return True

    def _get_alarm_group_definition(self, conn, tenant_id, _id):
        agd = self.agd_s
        query = (self.base_query
                 .select_from(self.base_query_from)
                 .where(agd.c.tenant_id == bindparam('b_tenant_id'))
                 .where(agd.c.id == bindparam('b_id'))
                 .where(agd.c.deleted_at == null()))

        row = conn.execute(query,
                           b_tenant_id=tenant_id,
                           b_id=_id).fetchone()

        if row is not None:
            return dict(row)
        else:
            raise exceptions.DoesNotExistException

    def _insert_into_actions(self, conn, alarm_group_definition_id, actions,
                             alarm_state):
        if actions is None or len(actions) == 0:
            return

        for action in actions:
            row = conn.execute(self.select_nm_query,
                               b_id=action.encode('utf8')).fetchone()
            if row is None:
                raise exceptions.InvalidUpdateException(
                    "Non-existent notification id {} submitted for {} "
                    "notification action".format(
                        action.encode('utf8'),
                        alarm_state.encode('utf8')))
            conn.execute(self.insert_agd_action_query,
                         b_alarm_group_definition_id=alarm_group_definition_id,
                         b_alarm_state=alarm_state.encode('utf8'),
                         b_action_id=action.encode('utf8'))

    def _insert_into_exclusions(self, conn, alarm_group_definition_id,
                                exclusions):
        if exclusions is None or len(exclusions) == 0:
            return

        exclusions_list = [[key, value] for key, value in exclusions.items()]
        for exclusion in exclusions_list:
            query = self.insert_agd_exclusion_query
            exclusion_name = exclusion[0].encode('utf8')
            exclusion_value = exclusion[1].encode('utf8')
            conn.execute(query,
                         b_alarm_group_definition_id=alarm_group_definition_id,
                         b_exclusion_name=exclusion_name,
                         b_value=exclusion_value)

    def _delete_alarm_group_definition_actions(self, conn, _id, action_state):
        conn.execute(self.delete_agd_action_query,
                     b_alarm_group_definition_id=_id,
                     b_alarm_state=action_state)

    def _delete_alarm_group_definition_exclusions(self, conn, _id):
        conn.execute(self.delete_agd_exclusion_query,
                     b_alarm_group_definition_id=_id)
