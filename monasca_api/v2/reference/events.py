# Copyright 2018 FUJITSU LIMITED
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

import falcon
from oslo_log import log

from monasca_api.api.core.events import bulk_processor
from monasca_api.api.core.events.model import prepare_message_to_sent
from monasca_api.v2.common.schemas import events_schema
from monasca_api.v2.reference import helpers

LOG = log.getLogger(__name__)


class Events(object):
    """Events.

    Events acts as a RESTful endpoint accepting messages contains
    collected events from the OpenStack message bus.
    Works as getaway for any further processing for accepted data.
    """
    VERSION = 'v1.0'
    SUPPORTED_CONTENT_TYPES = {'application/json'}

    def __init__(self):
        super(Events, self).__init__()

        self._processor = bulk_processor.EventsBulkProcessor()

    def on_post(self, req, res):
        """Accepts sent events as json.

        Accepts events sent to resource which should be sent
        to Kafka queue.

        :param req: current request
        :param res: current response
        """

        try:
            helpers.validate_authorization(req, ['api:events:post'])
            request_body = helpers.from_json(req)
            project_id = req.project_id
            events_schema.validate(request_body)
            messages = prepare_message_to_sent(request_body)
            self._processor.send_message(messages, event_project_id=project_id)
            res.status = falcon.HTTP_200
        except falcon.HTTPUnprocessableEntity as ex:
            LOG.error('Entire bulk package was rejected, unsupported body')
            LOG.exception(ex)
            raise ex
        except falcon.HTTPUnsupportedMediaType as ex:
            LOG.error('Entire bulk package was rejected, '
                      'unsupported media type')
            LOG.exception(ex)
            raise ex
        except Exception as ex:
            LOG.error('Entire bulk package was rejected')
            LOG.exception(ex)
            _title = ex.title if hasattr(ex, 'title') else None
            _descr = ex.description if hasattr(ex, 'description') else None
            raise falcon.HTTPError(falcon.HTTP_400,
                                   title=_title, description=_descr)

    @property
    def version(self):
        return getattr(self, 'VERSION')
