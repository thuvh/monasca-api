# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_serialization import jsonutils as json

from tempest.common import service_client


class MonascaClient(service_client.ServiceClient):

    def get_version(self):
        resp, response_body = self.get('')
        return resp, response_body

    def create_metrics(self, metrics):
        uri = 'metrics'
        request_body = json.dumps(metrics)
        resp, response_body = self.post(uri, request_body)
        return resp, response_body

    def list_metrics(self, query_params=None):
        uri = 'metrics'
        if query_params is not None:
            uri = uri + query_params
        resp, response_body = self.get(uri)
        return resp, json.loads(response_body)

    def list_measurements(self, query_params=None):
        uri = 'metrics/measurements'
        if query_params is not None:
            uri = uri + query_params
        resp, response_body = self.get(uri)
        return resp, json.loads(response_body)

    def list_statistics(self, query_params=None):
        uri = 'metrics/statistics'
        if query_params is not None:
            uri = uri + query_params
        resp, response_body = self.get(uri)
        return resp, json.loads(response_body)

    def create_alarm_definition(self,
                                name=None,
                                description=None,
                                expression=None,
                                match_by=None,
                                severity=None,
                                alarm_actions=None,
                                ok_actions=None,
                                undetermined_actions=None):
        uri = 'alarm-definitions'
        request_body = {}
        if name is not None:
            request_body['name'] = name
        if description is not None:
            request_body['description'] = description
        if expression is not None:
            request_body['expression'] = expression
        if match_by is not None:
            request_body['match_by'] = match_by
        if severity is not None:
            request_body['severity'] = severity
        if alarm_actions is not None:
            request_body['alarm_actions'] = alarm_actions
        if ok_actions is not None:
            request_body['ok_actions'] = ok_actions
        if undetermined_actions is not None:
            request_body['undetermined_actions'] = undetermined_actions
        resp, response_body = self.post(uri, json.dumps(request_body))
        return resp, json.loads(response_body)

    def list_alarm_definitions(self, query_params=None):
        uri = 'alarm-definitions'
        resp, response_body = self.get(uri)
        return resp, json.loads(response_body)

    def get_alarm_definition(self, id):
        uri = 'alarm-definitions/' + id
        resp, response_body = self.get(uri)
        return resp, json.loads(response_body)

    def delete_alarm_definition(self, id):
        uri = 'alarm-definitions/' + id
        resp, response_body = self.delete(uri)
        return resp, response_body

    def update_alarm_definition(self,
                                id,
                                name=None,
                                description=None,
                                expression=None,
                                actions_enabled=None,
                                match_by=None,
                                severity=None,
                                alarm_actions=None,
                                ok_actions=None,
                                undetermined_actions=None,
                                **kwargs):
        uri = 'alarm-definitions/' + id
        request_body = {}
        if name is not None:
            request_body['name'] = name
        if description is not None:
            request_body['description'] = description
        if expression is not None:
            request_body['expression'] = expression
        if actions_enabled is not None:
            request_body['actions_enabled'] = actions_enabled
        if match_by is not None:
            request_body['match_by'] = match_by
        if severity is not None:
            request_body['severity'] = severity
        if alarm_actions is not None:
            request_body['alarm_actions'] = alarm_actions
        if ok_actions is not None:
            request_body['ok_actions'] = ok_actions
        if undetermined_actions is not None:
            request_body['undetermined_actions'] = undetermined_actions

        for key, value in kwargs.iteritems():
            request_body[key] = value

        resp, response_body = self.patch(uri, json.dumps(request_body))
        return resp, json.loads(response_body)

    def create_notifications(self, notification):
        uri = 'notification-methods'
        request_body = json.dumps(notification)
        resp, response_body = self.post(uri, request_body)
        return resp, json.loads(response_body)

    def delete_notification_method(self, id):
        uri = 'notification-methods/' + id
        resp, response_body = self.delete(uri)
        return resp, response_body

    def get_notification_method(self, id):
        uri = 'notification-methods/' + id
        resp, response_body = self.get(uri)
        return resp, json.loads(response_body)

    def list_notification_methods(self, query_params=None):
        uri = 'notification-methods'
        if query_params is not None:
            uri = uri + query_params
        resp, response_body = self.get(uri)
        return resp, json.loads(response_body)

    def create_notification_method(self,
                                   name=None,
                                   type=None,
                                   address=None):
        uri = 'notification-methods'
        request_body = {}
        if name is not None:
            request_body['name'] = name
        if type is not None:
            request_body['type'] = type
        if address is not None:
            request_body['address'] = address
        resp, response_body = self.post(uri, json.dumps(request_body))
        return resp, json.loads(response_body)

    def update_notification_method(self,
                                   id,
                                   name=None,
                                   type=None,
                                   address=None):
        uri = 'notification-methods/' + id
        request_body = {}
        if name is not None:
            request_body['name'] = name
        if type is not None:
            request_body['type'] = type
        if address is not None:
            request_body['address'] = address
        resp, response_body = self.put(uri, json.dumps(request_body))
        return resp, json.loads(response_body)

    def list_alarms(self, query_params=None):
        uri = 'alarms'
        if query_params is not None:
            uri = uri + query_params
        resp, response_body = self.get(uri)
        return resp, json.loads(response_body)

    def get_alarm(self, id):
        uri = 'alarms/' + id
        resp, response_body = self.get(uri)
        return resp, json.loads(response_body)

    def delete_alarm(self, id):
        uri = 'alarms/' + id
        resp, response_body = self.delete(uri)
        return resp, response_body
