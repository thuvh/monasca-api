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
    alarm_silence_definitions_repository as asdr
from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories.sqla import models
from monasca_api.common.repositories.sqla import sql_repository
from sqlalchemy import MetaData, insert, update, delete
from sqlalchemy import select, text, bindparam, null

LOG = log.getLogger(__name__)


class AlarmSilenceDefinitionsRepository(sql_repository.SQLRepository,
                                        asdr.AlarmSilenceDefinitionsRepository
                                        ):
    def __init__(self):
        super(AlarmSilenceDefinitionsRepository, self).__init__()

        metadata = MetaData()
        self.asd = models.create_asd_model(metadata)
        self.asd_m = models.create_asdm_model(metadata)
        self.ar = models.create_ar_model(metadata)
        asd = self.asd
        asd_m = self.asd_m
        asd_s = asd.alias('asd')
        self.asd_s = asd_s
        ar = self.ar

        asdm_columns = [asd_m.c.matcher_name + text("'='") +
                        asd_m.c.matcher_value]

        asdmg = (select([asd_m.c.alarm_silence_definition_id,
                         models.group_concat(asdm_columns).label('matchers')])
                 .select_from(asd_m)
                 .group_by(asd_m.c.alarm_silence_definition_id).alias('asdmg'))

        self.base_query_from = (asd_s.outerjoin(
            asdmg, asdmg.c.alarm_silence_definition_id == asd_s.c.id))

        self.base_query = (select([asd_s.c.id,
                                   asd_s.c.name,
                                   asdmg.c.matchers,
                                   asd_s.c.start_time,
                                   asd_s.c.silence_duration]))

        self.insert_asd_query = \
            (insert(asd).values(
                id=bindparam('b_id'),
                tenant_id=bindparam('b_tenant_id'),
                name=bindparam('b_name'),
                start_time=bindparam('b_start_time'),
                silence_duration=bindparam('b_silence_duration'),
                created_at=bindparam('b_created_at'),
                updated_at=bindparam('b_updated_at')))

        self.insert_asdm_query = \
            (insert(asd_m).values(alarm_silence_definition_id=bindparam('b_alarm_silence_definition_id'),
                                  matcher_name=bindparam('b_matcher_name'),
                                  matcher_value=bindparam('b_matcher_value')))

        self.update_asd_query = (
            update(asd)
            .where(asd.c.tenant_id == bindparam('b_tenant_id'))
            .where(asd.c.id == bindparam('b_id')))

        self.delete_asdm_query = (
            delete(asd_m).where(asd_m.c.alarm_silence_definition_id ==
                                bindparam('b_alarm_silence_definition_id')))

        self.soft_delete_asd_query = (update(asd).where(
            asd.c.tenant_id == bindparam('b_tenant_id'))
            .where(asd.c.id == bindparam('b_id'))
            .where(asd.c.deleted_at == null())
            .values(deleted_at=datetime.datetime.utcnow()))
        self.delete_ar_query = (
            delete(ar).where(ar.c.alarm_rule_id == 
                             bindparam('b_alarm_silence_definition_id')))

    @sql_repository.sql_try_catch_block
    def create_alarm_silence_definition(self, tenant_id, name,
                                        matchers, start_time,
                                        silence_duration):
        with self._db_engine.begin() as conn:

            now = datetime.datetime.utcnow()
            alarm_silence_definition_id = uuidutils.generate_uuid()

            conn.execute(self.insert_asd_query,
                         b_id=alarm_silence_definition_id,
                         b_tenant_id=tenant_id,
                         b_name=name.encode('utf8'),
                         b_start_time=start_time.encode('utf8'),
                         b_silence_duration=silence_duration.encode('utf8'),
                         b_created_at=now,
                         b_updated_at=now)
            self._insert_into_matchers(conn, alarm_silence_definition_id,
                                       matchers)

            return alarm_silence_definition_id

    @sql_repository.sql_try_catch_block
    def get_alarm_silence_definitions(self, tenant_id, name=None, offset=None,
                                      limit=1000):

        with self._db_engine.connect() as conn:
            asd = self.asd_s
            query_from = self.base_query_from
            params = {'b_tenant_id': tenant_id}
            query = (self.base_query
                     .select_from(query_from)
                     .where(asd.c.tenant_id == bindparam('b_tenant_id'))
                     .where(asd.c.deleted_at == null()))
            if name:
                query = query.where(asd.c.name == bindparam('b_name'))
                params['b_name'] = name.encode('utf8')

            query = query.limit(bindparam('b_limit'))
            params['b_limit'] = limit + 1

            return [dict(row) for row in conn.execute(
                query, params).fetchall()]

    @sql_repository.sql_try_catch_block
    def get_alarm_silence_definition(self, tenant_id, _id):
        with self._db_engine.connect() as conn:
            return self._get_alarm_silence_definition(conn, tenant_id, _id)

    @sql_repository.sql_try_catch_block
    def update_or_patch_alarm_silence_definition(
            self, tenant_id, alarm_silence_definition_id, name, matchers,
            start_time, silence_duration, patch=False):

        with self._db_engine.begin() as conn:
            original_row = self._get_alarm_silence_definition(
                conn, tenant_id, alarm_silence_definition_id)

            # Get a common update time
            now = datetime.datetime.utcnow()

            if name is None:
                new_name = original_row['name']
            else:
                new_name = name.encode('utf8')

            if start_time is None:
                if patch:
                    new_start_time = original_row['start_time']
                else:
                    new_start_time = now  # default to current time
            else:
                new_start_time = start_time.encode('utf8')

            if silence_duration is None:
                if patch:
                    new_silence_duration = original_row['silence_duration']
                else:
                    new_silence_duration = '10m'  # default to 10 minutes
            else:
                new_silence_duration = silence_duration.encode('utf8')

            conn.execute(
                self.update_asd_query.values(
                    name=bindparam('b_name'),
                    start_time=bindparam('b_start_time'),
                    silence_duration=bindparam('b_silence_duration'),
                    updated_at=bindparam('b_updated_at')),
                b_name=new_name,
                b_start_time=new_start_time,
                b_silence_duration=new_silence_duration,
                b_updated_at=now,
                b_tenant_id=tenant_id,
                b_id=alarm_silence_definition_id)

            # Delete old matchers
            if patch:
                if matchers is not None:
                    self._delete_alarm_silence_definition_matchers(
                        conn, alarm_silence_definition_id)
            else:
                conn.execute(
                    self.delete_asdm_query,
                    b_alarm_silence_definition_id=alarm_silence_definition_id)

            # Insert new matchers
            self._insert_into_matchers(conn, alarm_silence_definition_id,
                                       matchers)

            asd = self.asd_s
            query = (self.base_query
                     .select_from(self.base_query_from)
                     .where(asd.c.tenant_id == bindparam('b_tenant_id'))
                     .where(asd.c.id == bindparam('b_id'))
                     .where(asd.c.deleted_at == null()))

            updated_row = conn.execute(query,
                                       b_id=alarm_silence_definition_id,
                                       b_tenant_id=tenant_id).fetchone()

            if updated_row is None:
                raise Exception("Failed to find current alarm silence "
                                "definition")

            # Delete old alarm rule relationships
            conn.execute(
                self.delete_ar_query,
                b_alarm_silence_definition_id=alarm_silence_definition_id)

            # Return the alarm silence definition
            return updated_row

    @sql_repository.sql_try_catch_block
    def delete_alarm_silence_definition(self, tenant_id,
                                        alarm_silence_definition_id):
        """Soft delete the alarm silence definition.
        """

        with self._db_engine.begin() as conn:
            cursor = conn.execute(self.soft_delete_asd_query,
                                  b_tenant_id=tenant_id,
                                  b_id=alarm_silence_definition_id)

            if cursor.rowcount < 1:
                return False

            # Delete old alarm rule relationships
            conn.execute(
                self.delete_ar_query,
                b_alarm_silence_definition_id=alarm_silence_definition_id)

            return True

    def _get_alarm_silence_definition(self, conn, tenant_id, _id):
        asd = self.asd_s
        query = (self.base_query
                 .where(asd.c.tenant_id == bindparam('b_tenant_id'))
                 .where(asd.c.id == bindparam('b_id'))
                 .where(asd.c.deleted_at == null()))

        row = conn.execute(query,
                           b_tenant_id=tenant_id,
                           b_id=_id).fetchone()

        if row is not None:
            return dict(row)
        else:
            raise exceptions.DoesNotExistException

    def _insert_into_matchers(self, conn, alarm_silence_definition_id,
                              matchers):
        if matchers is None:
            return

        matchers_list = [[key, value] for key, value in matchers.items()]
        for matcher in matchers_list:
            query = self.insert_asdm_query
            matcher_name = matcher[0].encode('utf8')
            matcher_value = matcher[1].encode('utf8')
            conn.execute(
                query,
                b_alarm_silence_definition_id=alarm_silence_definition_id,
                b_matcher_name=matcher_name,
                b_matcher_value=matcher_value)

    def _delete_alarm_silence_definition_matchers(self, conn, _id):
        conn.execute(self.delete_asdm_query,
                     b_alarm_silence_definition_id=_id)
