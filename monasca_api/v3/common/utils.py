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

import falcon
from oslo_log import log
import json
import simplejson

from monasca_api.common import exceptions
from monasca_api.common.repositories import exceptions as repo_exceptions

LOG = log.getLogger(__name__)


def exception_translator(fun):
    def try_it(*args, **kwargs):
        try:
            return fun(*args, **kwargs)

        except falcon.HTTPError:
            raise

        except repo_exceptions.DoesNotExistException:
            raise falcon.HTTPNotFound

        except repo_exceptions.MultipleMetricsException as ex:
            raise falcon.HTTPConflict("MultipleMetrics", ex.message)

        except repo_exceptions.AlreadyExistsException as ex:
            raise falcon.HTTPConflict(ex.__class__.__name__, ex.message)

        except repo_exceptions.InvalidUpdateException as ex:
            raise exceptions.HTTPUnprocessableEntityError(ex.__class__.__name__, ex.message)

        except repo_exceptions.RepositoryException as ex:
            LOG.exception(ex)
            msg = " ".join(map(str, ex.message.args))
            raise falcon.HTTPInternalServerError('The repository was unable '
                                                 'to process your request',
                                                 msg)

        except Exception as ex:
            LOG.exception(ex)
            raise falcon.HTTPInternalServerError('Service unavailable',
                                                 ex.message)

    return try_it


def parse_json_body(req, required_fields=None, defaults=None, validation=None):
    """Verifies structure of json data with option to add validation.

    :param req: a falcon request object
    :param required_fields: a list of required fields, will error if any not found.
    :param defaults: a dictionary of defaults, will add values only if key doesn't exist.
    :param validation: a function to use for validation accepting tenant_id and dictionary data
    """
    validate_json_content_type(req)
    data = parse_http_json_body(req)
    if required_fields is not None:
        for field in required_fields:
            if field not in data or data[field] is None:
                raise falcon.HTTPMissingParam(field)
    if defaults is not None:
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
    if validation is not None:
        validation(req=req, data=data)
    return data


def validate_json_content_type(req):
    if req.content_type not in ['application/json']:
        raise falcon.HTTPBadRequest('Bad request', 'Bad content type. Must be '
                                                   'application/json')


def parse_http_json_body(req):
    """Read from http request and return json.

    :param req: the http request.
    """
    try:
        msg = req.stream.read()
        return simplejson.loads(msg)
    except ValueError as ex:
        LOG.debug(ex)
        raise exceptions.HTTPUnprocessableEntityError(
            'Unprocessable Entity', 'Request body is not valid JSON')


def dumps_json_utf8(data):
    return json.dumps(data, ensure_ascii=False).encode('utf8')
