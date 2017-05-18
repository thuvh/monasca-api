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

from oslo_utils import uuidutils

from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories import group_rules_repository as grr
from monasca_api.common.repositories.sqla import models
from monasca_api.common.repositories.sqla import sql_repository
from sqlalchemy import MetaData, insert, update, delete
from sqlalchemy import select, text, bindparam, null


class GroupRulesRepository(sql_repository.SQLRepository,
                           grr.GroupRulesRepository):
    def __init__(self):
        super(GroupRulesRepository, self).__init__()

        metadata = MetaData()
        self.gr = models.create_gr_model(metadata)
        self.gr_a = models.create_gr_action_model(metadata)
        self.nm = models.create_nm_model(metadata)

        gr = self.gr
        gr_a = self.gr_a
        nm = self.nm
        gr_s = gr.alias('gr')
        self.gr_s = gr_s
        nm_s = nm.alias('nm')

        gr_aa = gr_a.alias('gr_aa')
        gr_action_a = (select([gr_aa.c.group_rule_id,
                               models.group_concat([gr_aa.c.action_id]).
                              label('alarm_actions')])
                       .select_from(gr_aa)
                       .where(gr_aa.c.alarm_state == text("'ALARM'"))
                       .group_by(gr_aa.c.group_rule_id)
                       .alias('gr_action_a'))

        gr_ao = gr_a.alias('gr_ao')
        gr_action_o = (select([gr_ao.c.group_rule_id,
                               models.group_concat([gr_ao.c.action_id]).
                               label('ok_actions')])
                       .select_from(gr_ao)
                       .where(gr_ao.c.alarm_state == text("'OK'"))
                       .group_by(gr_ao.c.group_rule_id)
                       .alias('gr_action_o'))

        gr_au = gr_a.alias('gr_au')
        gr_action_u = (select([gr_au.c.group_rule_id,
                               models.group_concat([gr_au.c.action_id]).
                               label('undetermined_actions')])
                       .select_from(gr_au)
                       .where(gr_au.c.alarm_state == text("'UNDETERMINED'"))
                       .group_by(gr_au.c.group_rule_id)
                       .alias('gr_action_u'))

        self.base_query_from = (
            gr_s.outerjoin(gr_action_a,
                           gr_action_a.c.group_rule_id == gr_s.c.id)
                .outerjoin(gr_action_o,
                           gr_action_o.c.group_rule_id == gr_s.c.id)
                .outerjoin(gr_action_u,
                           gr_action_u.c.group_rule_id == gr_s.c.id))

        self.base_query = (select([gr_s.c.id,
                                   gr_s.c.name,
                                   gr_s.c.expression,
                                   gr_s.c.group_wait,
                                   gr_s.c.repeat_interval,
                                   gr_s.c.description,
                                   gr_action_a.c.alarm_actions,
                                   gr_action_o.c.ok_actions,
                                   gr_action_u.c.undetermined_actions]))

        self.insert_gr_query = \
            (insert(gr).values(id=bindparam('b_id'),
                               tenant_id=bindparam('b_tenant_id'),
                               name=bindparam('b_name'),
                               expression=bindparam('b_expression'),
                               description=bindparam('b_description'),
                               group_wait=bindparam('b_group_wait'),
                               repeat_interval=bindparam('b_repeat_interval'),
                               created_at=bindparam('b_created_at'),
                               updated_at=bindparam('b_updated_at')))

        self.insert_gr_action_query = (insert(gr_a).values(
            group_rule_id=bindparam('b_group_rule_id'),
            alarm_state=bindparam('b_alarm_state'),
            action_id=bindparam('b_action_id')))

        self.select_nm_query = (select([nm_s.c.id])
                                .select_from(nm_s)
                                .where(nm_s.c.id == bindparam('b_id')))

        self.update_gr_query = (
            update(gr)
            .where(gr.c.tenant_id == bindparam('b_tenant_id'))
            .where(gr.c.id == bindparam('b_id')))

        self.delete_gr_query = (
            delete(gr_s)
            .where(gr_s.c.id == bindparam('b_id')))

        self.delete_gr_action_state_query = (
            delete(gr_a)
            .where(gr_a.c.group_rule_id == bindparam('b_group_rule_id'))
            .where(gr_a.c.alarm_state == bindparam('b_alarm_state')))

        self.delete_gr_action_query = (
            delete(gr_a)
            .where(gr_a.c.group_rule_id == bindparam('b_group_rule_id')))

        self.soft_delete_gr_query = (update(gr).where(
            gr.c.tenant_id == bindparam('b_tenant_id'))
            .where(gr.c.id == bindparam('b_id'))
            .where(gr.c.deleted_at == null())
            .values(deleted_at=datetime.datetime.utcnow()))

    @sql_repository.sql_try_catch_block
    def create_group_rule(self, tenant_id, name, expression, description,
                          group_wait, repeat_interval, alarm_actions,
                          ok_actions, undetermined_actions):
        with self._db_engine.begin() as conn:

            now = datetime.datetime.utcnow()
            group_rule_id = uuidutils.generate_uuid()

            conn.execute(self.insert_gr_query,
                         b_id=group_rule_id,
                         b_tenant_id=tenant_id,
                         b_name=name.encode('utf8'),
                         b_expression=expression.encode('utf8'),
                         b_description=description,
                         b_group_wait=group_wait.encode('utf8'),
                         b_repeat_interval=repeat_interval.encode('utf8'),
                         b_created_at=now,
                         b_updated_at=now)

            self._insert_into_actions(conn, group_rule_id,
                                      alarm_actions, u"ALARM")
            self._insert_into_actions(conn, group_rule_id,
                                      ok_actions, u"OK")
            self._insert_into_actions(conn, group_rule_id,
                                      undetermined_actions, u"UNDETERMINED")
            return group_rule_id

    @sql_repository.sql_try_catch_block
    def get_group_rules(self, tenant_id, name=None, offset=None, limit=None):
        with self._db_engine.connect() as conn:
            gr = self.gr_s
            query_from = self.base_query_from
            params = {'b_tenant_id': tenant_id}
            query = (self.base_query
                     .select_from(query_from)
                     .where(gr.c.tenant_id == bindparam('b_tenant_id'))
                     .where(gr.c.deleted_at == null()))
            if name:
                query = query.where(gr.c.name == bindparam('b_name'))
                params['b_name'] = name.encode('utf8')

            if offset:
                query = query.offset(bindparam('b_offset'))
                params['b_offset'] = offset

            if limit:
                query = query.limit(bindparam('b_limit'))
                params['b_limit'] = limit + 1

            return [dict(row) for row in conn.execute(
                query, params).fetchall()]

    @sql_repository.sql_try_catch_block
    def get_group_rule(self, tenant_id, rule_id):
        with self._db_engine.connect() as conn:
            return self._get_group_rule(conn, tenant_id, rule_id)

    @sql_repository.sql_try_catch_block
    def update_or_patch_group_rule(
            self, tenant_id, group_rule_id, name, expression, description,
            group_wait, repeat_interval, alarm_actions, ok_actions,
            undetermined_actions, patch=False):

        with self._db_engine.begin() as conn:
            original_row = self._get_group_rule(conn, tenant_id, group_rule_id)

            # Get a common update time
            now = datetime.datetime.utcnow()

            if not name:
                new_name = original_row['name']
            else:
                new_name = name.encode('utf8')

            if not description:
                new_description = original_row['description']
            else:
                new_description = description.encode('utf8')

            if not expression:
                new_expression = original_row['expression']
            else:
                new_expression = expression.encode('utf8')
                if new_expression != original_row['expression']:
                    msg = "expression must not change".encode('utf8')
                    raise exceptions.InvalidUpdateException(msg)

            if not group_wait:
                new_group_wait = original_row['group_wait']
            else:
                new_group_wait = group_wait.encode('utf8')

            if not repeat_interval:
                new_repeat_interval = original_row['repeat_interval']
            else:
                new_repeat_interval = repeat_interval.encode('utf8')

            conn.execute(
                self.update_gr_query.values(
                    name=bindparam('b_name'),
                    expression=bindparam('b_expression'),
                    description=bindparam('b_description'),
                    group_wait=bindparam('b_group_wait'),
                    repeat_interval=bindparam('b_repeat_interval'),
                    updated_at=bindparam('b_updated_at')),
                b_name=new_name,
                b_expression=new_expression,
                b_description=new_description,
                b_group_wait=new_group_wait,
                b_repeat_interval=new_repeat_interval,
                b_updated_at=now,
                b_tenant_id=tenant_id,
                b_id=group_rule_id)

            # Delete old actions
            if patch:
                if alarm_actions:
                    self._delete_group_rule_actions(
                        conn, group_rule_id, 'ALARM')
                if ok_actions:
                    self._delete_group_rule_actions(
                        conn, group_rule_id, 'OK')
                if undetermined_actions:
                    self._delete_group_rule_actions(
                        conn, group_rule_id, 'UNDETERMINED')
            else:
                conn.execute(self.delete_gr_action_query,
                             b_group_rule_id=group_rule_id)

            # Insert new actions
            if alarm_actions:
                self._insert_into_actions(conn,
                                          group_rule_id,
                                          alarm_actions,
                                          'ALARM')
            if ok_actions:
                self._insert_into_actions(conn,
                                          group_rule_id,
                                          ok_actions,
                                          'OK')
            if undetermined_actions:
                self._insert_into_actions(conn,
                                          group_rule_id,
                                          undetermined_actions,
                                          'UNDETERMINED')

            gr = self.gr_s
            query = (self.base_query
                     .select_from(self.base_query_from)
                     .where(gr.c.tenant_id == bindparam('b_tenant_id'))
                     .where(gr.c.id == bindparam('b_id'))
                     .where(gr.c.deleted_at == null()))

            updated_row = conn.execute(query,
                                       b_id=group_rule_id,
                                       b_tenant_id=tenant_id).fetchone()

            if not updated_row:
                raise Exception("Failed to find current group rule: group rule"
                                "id = {}".format(group_rule_id))

            # Return the group rule
            return updated_row

    @sql_repository.sql_try_catch_block
    def delete_group_rule(self, tenant_id, group_rule_id):
        """Soft delete the group rule.
        """

        with self._db_engine.begin() as conn:
            cursor = conn.execute(self.soft_delete_gr_query,
                                  b_tenant_id=tenant_id,
                                  b_id=group_rule_id)
            return cursor.rowcount > 0

    def _get_group_rule(self, conn, tenant_id, rule_id):
        gr = self.gr_s
        query = (self.base_query
                 .select_from(self.base_query_from)
                 .where(gr.c.tenant_id == bindparam('b_tenant_id'))
                 .where(gr.c.id == bindparam('b_id'))
                 .where(gr.c.deleted_at == null()))

        row = conn.execute(query,
                           b_tenant_id=tenant_id,
                           b_id=rule_id).fetchone()

        if row:
            return dict(row)
        else:
            raise exceptions.DoesNotExistException

    def _insert_into_actions(self, conn, group_rule_id, actions,
                             alarm_state):
        if not actions:
            return

        for action in actions:
            row = conn.execute(self.select_nm_query,
                               b_id=action.encode('utf8')).fetchone()
            if not row:
                raise exceptions.InvalidUpdateException(
                    "Non-existent notification id {} submitted for {} "
                    "notification action".format(
                        action.encode('utf8'),
                        alarm_state.encode('utf8')))
            conn.execute(self.insert_gr_action_query,
                         b_group_rule_id=group_rule_id,
                         b_alarm_state=alarm_state.encode('utf8'),
                         b_action_id=action.encode('utf8'))

    def _delete_group_rule_actions(self, conn, rule_id, action_state):
        conn.execute(self.delete_gr_action_state_query,
                     b_group_rule_id=rule_id,
                     b_alarm_state=action_state)
