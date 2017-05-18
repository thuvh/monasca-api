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
class SilenceRulesRepository(object):
    def __init__(self):
        super(SilenceRulesRepository, self).__init__()

    @abc.abstractmethod
    def create_silence_rule(self, tenant_id, name, expression, start_time,
                            duration_time, description):
        pass

    @abc.abstractmethod
    def get_silence_rules(self, tenant_id, name, offset, limit):
        pass

    @abc.abstractmethod
    def get_silence_rule(self, tenant_id, silence_rule_id):
        pass

    @abc.abstractmethod
    def delete_silence_rule(self, tenant_id, silence_rule_id):
        pass

    @abc.abstractmethod
    def update_or_patch_silence_rule(
            self, tenant_id, silence_rule_id, name, expression, start_time,
            duration_time, description, patch):
        pass
