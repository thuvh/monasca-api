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
class AlarmSilencingManagersRepository(object):
    def __init__(self):
        super(AlarmSilencingManagersRepository, self).__init__()

    @abc.abstractmethod
    def create_alarm_silencing_manager(self, tenant_id, name, matchers,
                                       start_time, end_time):
        pass

    @abc.abstractmethod
    def get_alarm_silencing_managers(self, tenant_id, name, offset, limit):
        pass

    @abc.abstractmethod
    def delete_alarm_silencing_manager(self, tenant_id,
                                       alarm_silencing_manager_id):
        pass

    @abc.abstractmethod
    def update_or_patch_alarm_silencing_manager(
            self, tenant_id, alarm_silencing_manager_id, name, matchers,
            start_time, end_time):
        pass
