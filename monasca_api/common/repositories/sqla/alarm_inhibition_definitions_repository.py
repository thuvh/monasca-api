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

from monasca_api.common.repositories import \
    alarm_inhibition_definitions_repository as aidr
from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories.sqla import models
from monasca_api.common.repositories.sqla import sql_repository
from sqlalchemy import MetaData, insert, update
from sqlalchemy import select, text, bindparam, null


class AlarmInhibitionDefinitionsRepository(sql_repository.SQLRepository, aidr.AlarmInhibitionDefinitionsRepository):
    def __init__(self):
        super(AlarmInhibitionDefinitionsRepository, self).__init__()

        metadata = MetaData()
        self.ard = models.create_ard_model(metadata)
        self.aid = models.create_aid_model(metadata)
        self.aid_sm = models.create_aidsm_model(metadata)
        self.aid_tm = models.create_aidtm_model(metadata)
        self.aid_e = models.create_aid_exclusion_model(metadata)

        ard = self.ard
        aid = self.aid
        aid_sm = self.aid_sm
        aid_tm = self.aid_tm
        aid_e = self.aid_e
        aid_s = aid.alias('aid')
        self.aid_s = aid_s

        aidsm_columns = [aid_sm.c.source_name + text("'='") +
                         aid_sm.c.source_value]
        aidtm_columns = [aid_tm.c.target_name + text("'='") +
                         aid_tm.c.target_value]
        aide_columns = [aid_e.c.exclusion_name + text("'='") +
                        aid_e.c.value]

        aidsmg = (select([aid_sm.c.alarm_inhibition_definition_id,
                          models.group_concat(aidsm_columns).label(
                              'source_match')])
                  .select_from(aid_sm)
                  .group_by(aid_sm.c.alarm_inhibition_definition_id).alias(
            'aidsmg'))

        aidtmg = (select([aid_tm.c.alarm_inhibition_definition_id,
                          models.group_concat(aidtm_columns).label(
                              'target_match')])
                  .select_from(aid_tm)
                  .group_by(aid_tm.c.alarm_inhibition_definition_id).alias(
            'aidtmg'))
        aideg = (select([aid_e.c.alarm_inhibition_definition_id,
                         models.group_concat(aide_columns).label(
                             'exclusion')])
                 .select_from(aid_e)
                 .group_by(aid_e.c.alarm_inhibition_definition_id).alias(
            'aideg'))

        self.base_query_from = (ard.outerjoin(
            aid_s, aid_s.c.rule_id ==
            ard.c.id).outerjoin(
            aidsmg, aidsmg.c.alarm_inhibition_definition_id ==
            ard.c.id).outerjoin(
            aidtmg, aidtmg.c.alarm_inhibition_definition_id ==
            ard.c.id).outerjoin(
            aideg, aideg.c.alarm_inhibition_definition_id ==
            ard.c.id))

        self.base_query = (select([ard.c.id,
                                   ard.c.name,
                                   ard.c.description,
                                   aid_s.c.equal,
                                   aidsmg.c.source_match,
                                   aidtmg.c.target_match,
                                   aideg.c.exclusion]))

        self.insert_ard_query = \
            (insert(ard).values(id=bindparam('b_id'),
                                tenant_id=bindparam('b_tenant_id'),
                                name=bindparam('b_name'),
                                description=bindparam('b_description'),
                                created_at=bindparam('b_created_at'),
                                updated_at=bindparam('b_updated_at')))

        self.insert_aid_query = \
            (insert(aid).values(rule_id=bindparam('b_rule_id'),
                                equal=bindparam('b_equal')))

        b_aid_id = bindparam('b_alarm_inhibition_definition_id')
        self.insert_aidsm_query = \
            (insert(aid_sm).values(alarm_inhibition_definition_id=b_aid_id,
                                   source_name=bindparam('b_source_name'),
                                   source_value=bindparam('b_source_value')))

        self.insert_aidtm_query = \
            (insert(aid_tm).values(alarm_inhibition_definition_id=b_aid_id,
                                   target_name=bindparam('b_target_name'),
                                   target_value=bindparam('b_target_value')))

        self.insert_aide_query = \
            (insert(aid_e).values(alarm_inhibition_definition_id=b_aid_id,
                                  exclusion_name=bindparam('b_exclusion_name'),
                                  value=bindparam('b_value')))

        self.update_ard_query = (
            update(ard).where(ard.c.tenant_id == bindparam('b_tenant_id'))
                       .where(ard.c.id == bindparam('b_id')))

        self.soft_delete_ard_query = (update(ard).where(
            ard.c.tenant_id == bindparam('b_tenant_id'))
            .where(ard.c.id == bindparam('b_id'))
            .where(ard.c.deleted_at == null())
            .values(deleted_at=datetime.datetime.utcnow()))

    @sql_repository.sql_try_catch_block
    def create_alarm_inhibition_definition(self, tenant_id, name, description,
                                           equal, source_match, target_match,
                                           exclusions):
        with self._db_engine.begin() as conn:
            now = datetime.datetime.utcnow()
            aid_id = uuidutils.generate_uuid()

            conn.execute(self.insert_ard_query,
                         b_id=aid_id,
                         b_tenant_id=tenant_id,
                         b_name=name.encode('utf8'),
                         b_description=description.encode('utf8'),
                         b_created_at=now,
                         b_updated_at=now)

            conn.execute(self.insert_aid_query,
                         b_rule_id=aid_id,
                         b_equal=",".join(equal).encode('utf8'))

            self._insert_into_source_match(conn, aid_id, source_match)

            self._insert_into_target_match(conn, aid_id, target_match)

            self._insert_into_exclusions(conn, aid_id, exclusions)

            return aid_id

    @sql_repository.sql_try_catch_block
    def get_alarm_inhibition_definitions(self, tenant_id, name=None,
                                         offset=None, limit=1000):
        with self._db_engine.connect() as conn:
            ard = self.ard
            query_from = self.base_query_from
            params = {'b_tenant_id': tenant_id}
            query = (self.base_query
                     .select_from(query_from)
                     .where(ard.c.tenant_id == bindparam('b_tenant_id'))
                     .where(ard.c.deleted_at == null()))
            if name:
                query = query.where(ard.c.name == bindparam('b_name'))
                params['b_name'] = name.encode('utf8')

            if offset:
                query = query.offset(bindparam('b_offset'))
                params['b_offset'] = offset

            order_columns = [ard.c.id]
            query = query.order_by(*order_columns)
            query = query.limit(bindparam('b_limit'))
            params['b_limit'] = limit + 1

            return [dict(row) for row in conn.execute(query, params).fetchall()]

    @sql_repository.sql_try_catch_block
    def get_alarm_inhibition_definition(self, tenant_id, _id):
        with self._db_engine.connect() as conn:
            return self._get_alarm_inhibition_definition(conn, tenant_id, _id)

    @sql_repository.sql_try_catch_block
    def update_or_patch_alarm_inhibition_definition(
            self, tenant_id, aid_id, name, description,
            equal, source_match, target_match, exclusions,
            patch=False):

        with self._db_engine.begin() as conn:
            original_row = self._get_alarm_inhibition_definition(
                conn, tenant_id, aid_id)

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

            if new_description != original_row['description']:
                msg = "description must not change.".encode('utf8')
                raise exceptions.InvalidUpdateExcaption(msg)

            if equal and equal != original_row['equal']:
                msg = "equal must not change.".encode('utf8')
                raise exceptions.InvalidUpdateExcaption(msg)

            if source_match and source_match != original_row['source_match']:
                msg = "source match must not change.".encode('utf8')
                raise exceptions.InvalidUpdateExcaption(msg)

            if target_match and target_match != original_row['target_match']:
                msg = "target match must not change.".encode('utf8')
                raise exceptions.InvalidUpdateExcaption(msg)

            if exclusions and exclusions != original_row['exclusions']:
                msg = "exclusions match must not change.".encode('utf8')
                raise exceptions.InvalidUpdateExcaption(msg)

            conn.execute(
                self.update_ard_query
                    .values(name=bindparam('b_name'),
                            description=bindparam('b_description'),
                            updated_at=bindparam('b_updated_at')),
                b_name=new_name,
                b_description=new_description,
                b_updated_at=now,
                b_tenant_id=tenant_id,
                b_id=aid_id)

            ard = self.ard
            query = (self.base_query
                     .select_from(self.base_query_from)
                     .where(ard.c.tenant_id == bindparam('b_tenant_id'))
                     .where(ard.c.id == bindparam('b_id'))
                     .where(ard.c.deleted_at == null()))

            updated_row = conn.execute(query,
                                       b_id=aid_id,
                                       b_tenant_id=tenant_id).fetchone()

            if not updated_row:
                raise Exception("Failed to find current alarm inhibition "
                                "definition")

            # Return the alarm inhibition definition
            return updated_row

    @sql_repository.sql_try_catch_block
    def delete_alarm_inhibition_definition(self, tenant_id,
                                           aid_id):
        """Soft delete the alarm inhibition definition.
        """

        with self._db_engine.begin() as conn:
            cursor = conn.execute(self.soft_delete_ard_query,
                                  b_tenant_id=tenant_id,
                                  b_id=aid_id)

            if cursor.rowcount < 1:
                return False

            return True

    def _insert_into_source_match(
            self, conn, aid_id, source_match):
        if not source_match:
            return

        source_match_list = [[key, value] for key, value in
                             source_match.items()]
        for source_match in source_match_list:
            query = self.insert_aidsm_query
            source_name = source_match[0].encode('utf8')
            source_value = source_match[1].encode('utf8')
            conn.execute(query,
                         b_alarm_inhibition_definition_id=aid_id,
                         b_source_name=source_name,
                         b_source_value=source_value)

    def _insert_into_target_match(
            self, conn, aid_id, target_match):
        if not target_match:
            return

        target_match_list = [[key, value] for key, value in
                             target_match.items()]
        for target_match in target_match_list:
            query = self.insert_aidtm_query
            target_name = target_match[0].encode('utf8')
            target_value = target_match[1].encode('utf8')
            conn.execute(query,
                         b_alarm_inhibition_definition_id=aid_id,
                         b_target_name=target_name,
                         b_target_value=target_value)

    def _insert_into_exclusions(
            self, conn, alarm_inhibition_definition_id, exclusions):
        if not exclusions:
            return

        exclusions_list = [[key, value] for key, value in exclusions.items()]
        for exclusion in exclusions_list:
            query = self.insert_aide_query
            exclusion_name = exclusion[0].encode('utf8')
            exclusion_value = exclusion[1].encode('utf8')
            conn.execute(query,
                         b_alarm_inhibition_definition_id=alarm_inhibition_definition_id,
                         b_exclusion_name=exclusion_name,
                         b_value=exclusion_value)

    def _get_alarm_inhibition_definition(self, conn, tenant_id, _id):
        ard = self.ard
        query = (self.base_query
                 .select_from(self.base_query_from)
                 .where(ard.c.tenant_id == bindparam('b_tenant_id'))
                 .where(ard.c.id == bindparam('b_id'))
                 .where(ard.c.deleted_at == null()))

        row = conn.execute(query,
                           b_tenant_id=tenant_id,
                           b_id=_id).fetchone()

        if row:
            return dict(row)
        else:
            raise exceptions.DoesNotExistException
