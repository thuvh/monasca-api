# Copyright 2013 IBM Corp
#
# Author: Tong Li <litong01@us.ibm.com>
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

from monasca.common import resource_api


class MyAPI(object):
    @resource_api.Restify(path='/v2/metrics')
    def on_get_metrics(self, res, req):
        pass

    @resource_api.Restify(path='/v2/metrics', method='post')
    def on_post_metrics(self, res, req):
        pass

    def on_do1(self):
        pass
