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
PAGE_LIMIT = 10000
# Brief description of the group rule
GROUP_RULE_DESCRIPTION = ''
# Brief description of the silence rule
SILENCE_RULE_DESCRIPTION = ''
# Brief description of the inhibit rule
INHIBIT_RULE_DESCRIPTION = ''
# The length of time the silence should effect alarm state transitions.
# Defaults to '10m', also can be specified in "2d3h4m5s" format.
SILENCE_RULE_SILENCE_DURATION = '10m'
# Group wait specifies the window that the Notification Engine waits for
# notifications to pull down a batch to be examined
GROUP_RULE_GROUP_WAIT = '30s'
# Repeat interval specifies the wait time to resend the group notification.
GROUP_RULE_REPEAT_INTERVAL = '2h'
# Array of notification method IDs that are invoked when the group of alarms
# transition to any state.
GROUP_RULE_ACTIONS = []
