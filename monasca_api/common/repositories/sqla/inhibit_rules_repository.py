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
from monasca_api.common.repositories import inhibit_rules_repository as irr
from monasca_api.common.repositories.sqla import models
from monasca_api.common.repositories.sqla import sql_repository
from sqlalchemy import MetaData, insert, update
from sqlalchemy import select, bindparam, null


class InhibitRulesRepository(sql_repository.SQLRepository,
                             irr.InhibitRulesRepository):
    def __init__(self):
        super(InhibitRulesRepository, self).__init__()

        metadata = MetaData()
        self.ir = models.create_ir_model(metadata)

        ir = self.ir
        ir_s = ir.alias('ir')
        self.ir_s = ir_s

        self.base_query = (select([ir_s.c.id,
                                   ir_s.c.name,
                                   ir_s.c.expression,
                                   ir_s.c.description]))

        self.insert_ir_query = \
            (insert(ir).values(id=bindparam('b_id'),
                               tenant_id=bindparam('b_tenant_id'),
                               name=bindparam('b_name'),
                               expression=bindparam('b_expression'),
                               description=bindparam('b_description'),
                               created_at=bindparam('b_created_at'),
                               updated_at=bindparam('b_updated_at')))
        self.update_or_patch_ir_query = (
            update(ir)
            .where(ir.c.tenant_id == bindparam('b_tenant_id'))
            .where(ir.c.id == bindparam('b_id')))

        self.soft_delete_ir_query = (update(ir).where(
            ir.c.tenant_id == bindparam('b_tenant_id'))
            .where(ir.c.id == bindparam('b_id'))
            .where(ir.c.deleted_at == null())
            .values(deleted_at=datetime.datetime.utcnow()))

    @sql_repository.sql_try_catch_block
    def create_inhibit_rule(self, tenant_id, name, expression, description):
        with self._db_engine.begin() as conn:
            now = datetime.datetime.utcnow()
            ir_id = uuidutils.generate_uuid()

            conn.execute(self.insert_ir_query,
                         b_id=ir_id,
                         b_tenant_id=tenant_id,
                         b_name=name.encode('utf8'),
                         b_expression=expression.encode('utf8'),
                         b_description=description.encode('utf8'),
                         b_created_at=now,
                         b_updated_at=now)
            return ir_id

    @sql_repository.sql_try_catch_block
    def get_inhibit_rules(self, tenant_id, name=None, offset=None, limit=None):
        with self._db_engine.connect() as conn:
            irs = self.ir_s
            params = {'b_tenant_id': tenant_id}
            query = (self.base_query
                     .where(irs.c.tenant_id == bindparam('b_tenant_id'))
                     .where(irs.c.deleted_at == null()))
            if name:
                query = query.where(irs.c.name == bindparam('b_name'))
                params['b_name'] = name.encode('utf8')

            if offset:
                query = query.offset(bindparam('b_offset'))
                params['b_offset'] = offset

            if limit:
                query = query.limit(bindparam('b_limit'))
                params['b_limit'] = limit + 1

            order_columns = [irs.c.id]
            query = query.order_by(*order_columns)

            return [dict(row) for row in conn.execute(query, params).fetchall()]

    @sql_repository.sql_try_catch_block
    def get_inhibit_rule(self, tenant_id, rule_id):
        with self._db_engine.connect() as conn:
            return self._get_inhibit_rule(conn, tenant_id, rule_id)

    @sql_repository.sql_try_catch_block
    def update_or_patch_inhibit_rule(self, tenant_id, inhibit_rule_id, name,
                                     expression, description, patch=False):

        with self._db_engine.begin() as conn:
            original_row = self._get_inhibit_rule(
                conn, tenant_id, inhibit_rule_id)

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
                    msg = "expression must not change {} vs {}.".format(
                        expression, original_row['expression']).encode('utf8')
                    raise exceptions.InvalidUpdateException(msg)

            conn.execute(
                self.update_or_patch_ir_query
                    .values(name=bindparam('b_name'),
                            expression=bindparam('b_expression'),
                            description=bindparam('b_description'),
                            updated_at=bindparam('b_updated_at')),
                b_name=new_name,
                b_expression=new_expression,
                b_description=new_description,
                b_updated_at=now,
                b_tenant_id=tenant_id,
                b_id=inhibit_rule_id)

            irs = self.ir_s
            query = (self.base_query
                     .where(irs.c.tenant_id == bindparam('b_tenant_id'))
                     .where(irs.c.id == bindparam('b_id'))
                     .where(irs.c.deleted_at == null()))

            updated_row = conn.execute(query,
                                       b_id=inhibit_rule_id,
                                       b_tenant_id=tenant_id).fetchone()

            if not updated_row:
                raise Exception("Failed to find current inhibit rule")

            # Return the inhibit rule
            return updated_row

    @sql_repository.sql_try_catch_block
    def delete_inhibit_rule(self, tenant_id, ir_id):
        """Soft delete the inhibit rule.
        """

        with self._db_engine.begin() as conn:
            cursor = conn.execute(self.soft_delete_ir_query,
                                  b_tenant_id=tenant_id,
                                  b_id=ir_id)

            return cursor.rowcount > 0

    def _get_inhibit_rule(self, conn, tenant_id, _id):
        irs = self.ir_s
        query = (self.base_query
                 .where(irs.c.tenant_id == bindparam('b_tenant_id'))
                 .where(irs.c.id == bindparam('b_id'))
                 .where(irs.c.deleted_at == null()))

        row = conn.execute(query,
                           b_tenant_id=tenant_id,
                           b_id=_id).fetchone()

        if row:
            return dict(row)
        else:
            raise exceptions.DoesNotExistException
