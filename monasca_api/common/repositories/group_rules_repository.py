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

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class GroupRulesRepository(object):
    def __init__(self):
        super(GroupRulesRepository, self).__init__()

    @abc.abstractmethod
    def create_group_rule(self, tenant_id, name, expression, description,
                          group_wait, repeat_interval, alarm_actions,
                          ok_actions, undetermined_actions):
        pass

    @abc.abstractmethod
    def get_group_rules(self, tenant_id, name, offset, limit):
        pass

    @abc.abstractmethod
    def get_group_rule(self, tenant_id, group_rule_id):
        pass

    @abc.abstractmethod
    def delete_group_rule(self, tenant_id, group_rule_id):
        pass

    @abc.abstractmethod
    def update_or_patch_group_rule(
            self, tenant_id, group_rule_id, name, expression, description,
            group_wait, repeat_interval, alarm_actions, ok_actions,
            undetermined_actions, patch):
        pass
