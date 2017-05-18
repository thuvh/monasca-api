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
from monasca_api.common.repositories import silence_rules_repository as srr
from monasca_api.common.repositories.sqla import models
from monasca_api.common.repositories.sqla import sql_repository
from sqlalchemy import MetaData, insert, update
from sqlalchemy import select, bindparam, null


class SilenceRulesRepository(sql_repository.SQLRepository,
                             srr.SilenceRulesRepository):
    def __init__(self):
        super(SilenceRulesRepository, self).__init__()

        metadata = MetaData()
        self.sr = models.create_sr_model(metadata)
        sr = self.sr
        sr_s = sr.alias('sr')
        self.sr_s = sr_s

        self.base_query = (select([sr_s.c.id,
                                   sr_s.c.name,
                                   sr_s.c.expression,
                                   sr_s.c.start_time,
                                   sr_s.c.silence_duration,
                                   sr_s.c.description]))

        self.insert_sr_query = \
            (insert(sr).values(
                id=bindparam('b_id'),
                tenant_id=bindparam('b_tenant_id'),
                name=bindparam('b_name'),
                expression=bindparam('b_expression'),
                created_at=bindparam('b_created_at'),
                updated_at=bindparam('b_updated_at'),
                start_time=bindparam('b_start_time'),
                silence_duration=bindparam('b_silence_duration'),
                description=bindparam('b_description')))

        self.update_sr_query = (
            update(sr)
            .where(sr.c.tenant_id == bindparam('b_tenant_id'))
            .where(sr.c.id == bindparam('b_id')))

        self.soft_delete_sr_query = (update(sr).where(
            sr.c.tenant_id == bindparam('b_tenant_id'))
            .where(sr.c.id == bindparam('b_id'))
            .where(sr.c.deleted_at == null())
            .values(deleted_at=datetime.datetime.utcnow()))

    @sql_repository.sql_try_catch_block
    def create_silence_rule(self, tenant_id, name, expression, description,
                            start_time, silence_duration):
        with self._db_engine.begin() as conn:
            now = datetime.datetime.utcnow()
            silence_rule_id = uuidutils.generate_uuid()

            conn.execute(self.insert_sr_query,
                         b_id=silence_rule_id,
                         b_tenant_id=tenant_id,
                         b_name=name.encode('utf8'),
                         b_expression=expression.encode('utf8'),
                         b_description=description.encode('utf8'),
                         b_start_time=start_time,
                         b_silence_duration=silence_duration.encode('utf8'),
                         b_created_at=now,
                         b_updated_at=now)
            return silence_rule_id

    @sql_repository.sql_try_catch_block
    def get_silence_rules(self, tenant_id, name=None, offset=None, limit=None):
        with self._db_engine.connect() as conn:
            sr = self.sr_s
            params = {'b_tenant_id': tenant_id}
            query = (self.base_query
                     .where(sr.c.tenant_id == bindparam('b_tenant_id'))
                     .where(sr.c.deleted_at == null()))
            if name:
                query = query.where(sr.c.name == bindparam('b_name'))
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
    def get_silence_rule(self, tenant_id, rule_id):
        with self._db_engine.connect() as conn:
            return self._get_silence_rule(conn, tenant_id, rule_id)

    @sql_repository.sql_try_catch_block
    def update_or_patch_silence_rule(
            self, tenant_id, silence_rule_id, name, expression, description,
            start_time, silence_duration, patch=False):

        with self._db_engine.begin() as conn:
            original_row = self._get_silence_rule(
                conn, tenant_id, silence_rule_id)

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
                    msg = "expression must not change.".encode('utf8')
                    raise exceptions.InvalidUpdateException(msg)

            if not start_time:
                new_start_time = original_row['start_time']
            else:
                new_start_time = start_time.encode('utf8')

            if not silence_duration:
                new_silence_duration = original_row['silence_duration']
            else:
                new_silence_duration = silence_duration.encode('utf8')

            conn.execute(
                self.update_sr_query.values(
                    name=bindparam('b_name'),
                    expression=bindparam('b_expression'),
                    description=bindparam('b_description'),
                    start_time=bindparam('b_start_time'),
                    silence_duration=bindparam('b_silence_duration'),
                    updated_at=bindparam('b_updated_at')),
                b_name=new_name,
                b_expression=new_expression,
                b_description=new_description,
                b_start_time=new_start_time,
                b_silence_duration=new_silence_duration,
                b_updated_at=now,
                b_tenant_id=tenant_id,
                b_id=silence_rule_id)

            srs = self.sr_s
            query = (self.base_query
                     .where(srs.c.tenant_id == bindparam('b_tenant_id'))
                     .where(srs.c.id == bindparam('b_id'))
                     .where(srs.c.deleted_at == null()))

            updated_row = conn.execute(query,
                                       b_id=silence_rule_id,
                                       b_tenant_id=tenant_id).fetchone()

            if not updated_row:
                raise Exception("Failed to find current silence rule")

            # Return the silence rule
            return updated_row

    @sql_repository.sql_try_catch_block
    def delete_silence_rule(self, tenant_id, silence_rule_id):
        """Soft delete the silence rule.
        """

        with self._db_engine.begin() as conn:
            cursor = conn.execute(self.soft_delete_sr_query,
                                  b_tenant_id=tenant_id,
                                  b_id=silence_rule_id)

            return cursor.rowcount > 0

    def _get_silence_rule(self, conn, tenant_id, rule_id):
        sr = self.sr_s
        query = (self.base_query
                 .where(sr.c.tenant_id == bindparam('b_tenant_id'))
                 .where(sr.c.id == bindparam('b_id'))
                 .where(sr.c.deleted_at == null()))

        row = conn.execute(query,
                           b_tenant_id=tenant_id,
                           b_id=rule_id).fetchone()

        if row:
            return dict(row)
        else:
            raise exceptions.DoesNotExistException
