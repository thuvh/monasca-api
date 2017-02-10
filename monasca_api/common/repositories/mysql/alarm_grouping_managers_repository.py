# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
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

from monasca_common.repositories.mysql import mysql_repository
from oslo_utils import uuidutils

from monasca_api.common.repositories import alarm_grouping_managers_repository as adr
from monasca_api.common.repositories import exceptions


class AlarmGroupingManagersRepository(mysql_repository.MySQLRepository,
                                      adr.AlarmGroupingManagersRepository):
    base_query = """
        """

    def __init__(self):
        super(AlarmGroupingManagersRepository, self).__init__()

    @mysql_repository.mysql_try_catch_block
    def create_alarm_grouping_manager(self, tenant_id, name, matchers,
                                      group_wait, repeat_interval, exclusions,
                                      actions):
        cnxn, cursor = self._get_cnxn_cursor_tuple()
        with cnxn:
            now = datetime.datetime.utcnow()
            alarm_grouping_manager_id = uuidutils.generate_uuid()
            cursor.execute("""insert into alarm_grouping_manager(
                                   id,
                                   tenant_id,
                                   name,
                                   matchers,
                                   group_wait,
                                   repeat_interval,
                                   created_at,
                                   updated_at)
                                   values (%s, %s, %s, %s, %s, %s, %s, %s)
                                   """, (
                alarm_grouping_manager_id, tenant_id, name.encode('utf8'),
                ",".join(matchers).encode('utf8'), group_wait.encode('utf8'),
                repeat_interval.encode('utf8'), now, now))

            for exclusion in exclusions:
                parsed_exclusion = exclusion.split(',')
                cursor.execute("""insert into
                alarm_grouping_manager_exclusion(
                            alarm_grouping_manager_id,
                            exclusion_name,
                            exclusion_value)
                            values(%s,%s,%s)""", (
                    alarm_grouping_manager_id,
                    parsed_exclusion[0].encode('utf8'),
                    parsed_exclusion[1].encode('utf8')))

            self._insert_into_actions(cursor, alarm_grouping_manager_id,
                                      actions)

            return alarm_grouping_manager_id
        pass

    def _insert_into_actions(self, cursor, alarm_grouping_manager_id, actions):
        if actions is None:
            return

        for action in actions:
            cursor.execute("select id from notification_method where id = %s",
                           (action.encode('utf8'),))
            row = cursor.fetchone()
            if not row:
                raise exceptions.RepositoryException(
                    "Non-existent notification id {} submitted".format(
                        action.encode('utf8')))
            cursor.execute("""insert into action(
                                   alarm_grouping_manager_id,
                                   action_id)
                                   values(%s,%s)""", (
                alarm_grouping_manager_id, action.encode('utf8')))

'''
    @mysql_repository.mysql_try_catch_block
    def get_alarm_grouping_manager(self, tenant_id, alarm_grouping_manager_id):
        params = [tenant_id, alarm_grouping_manager_id]

        where_clause = """ where ad.tenant_id = %s
                            and ad.id = %s
                            and deleted_at is NULL """

        query = AlarmGroupingManagersRepository.base_query + where_clause

        rows = self._execute_query(query, params)

        if rows:
            return rows[0]
        else:
            raise exceptions.DoesNotExistException

    @mysql_repository.mysql_try_catch_block
    def get_alarm_grouping_managers(self, tenant_id, name, matchers, offset,
                                    limit):
        pass

    @mysql_repository.mysql_try_catch_block
    def delete_alarm_grouping_manager(self, tenant_id,
                                      alarm_grouping_manager_id):
        pass

    @mysql_repository.mysql_try_catch_block
    def create_alarm_grouping_manager(self, tenant_id, name, matchers,
                                      group_wait, repeat_interval, exclusions,
                                      actions):
        pass

    @mysql_repository.mysql_try_catch_block
    def update_or_patch_alarm_definition(self, tenant_id,
                                         alarm_grouping_manager_id, name,
                                         matchers, group_wait,
                                         repeat_interval, exclusions, actions,
                                         patch=False):
        pass
'''
