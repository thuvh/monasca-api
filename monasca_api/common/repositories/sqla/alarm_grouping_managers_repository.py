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

from oslo_log import log

from monasca_api.common.repositories import alarm_grouping_managers_repository\
    as adr
from monasca_api.common.repositories import exceptions
from monasca_api.common.repositories.sqla import models
from monasca_api.common.repositories.sqla import sql_repository
from sqlalchemy import MetaData, update, delete, insert
from sqlalchemy import select, text, bindparam, null, literal_column

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
        nm_s = nm.alias('nm')

        agma = (select([agm_a.c.alarm_grouping_manager_id,
                        models.group_concat([agm_a.c.action_id]).label(
                            'actions')])
                .select_from(agm_a)
                .group_by(agm_a.c.alarm_grouping_manager_id)
                .alias('agma'))

        self.base_query_from = (agm_s.outerjoin(
            agm_a, agm_a.c.alarm_grouping_manager_id == agm_s.c.id))

        self.base_query = (select([agm_s.c.id,
                                   agm_s.c.name,
                                   agm_s.c.matchers,
                                   agm_s.c.group_wait,
                                   agm_s.c.repeat_interval,
                                   agm_s.c.exclusions,
                                   agma.c.actions]))

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

            exclusions_list = self._exclusions_to_list(exclusions)
            for exclusion in exclusions_list:
                query = self.create_alarm_grouping_manager_insert_agme_query
                exclusion_name = exclusion[0].encode('utf8')
                exclusion_value = exclusion[1].encode('utf8')
                LOG.debug("exclusion_name = {}".format(exclusion_name))
                LOG.debug("exclusion_value = {}".format(exclusion_value))
                LOG.debug("alarm_grouping_manager_id = {}".format(alarm_grouping_manager_id))
                conn.execute(query,
                             b_alarm_grouping_manager_id=alarm_grouping_manager_id,
                             b_exclusion_name=exclusion_name,
                             b_value=exclusion_value)

            self._insert_into_actions(conn, alarm_grouping_manager_id, actions)
            return alarm_grouping_manager_id

    def _exclusions_to_list(self, exclusions):
        if exclusions:
            return [[key, value] for key, value in exclusions.items()]
        else:
            return []

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
