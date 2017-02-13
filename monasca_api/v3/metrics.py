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
from monasca_common.simport import simport
from monasca_common.validation import metrics as metric_validation
from oslo_config import cfg
from oslo_log import log
import simplejson

from monasca_api.common.messaging import exceptions as message_queue_exceptions
from monasca_api.common.messaging.message_formats import metrics as metrics_message
from monasca_api.v3.common import auth
from monasca_api.v3.common import pagination
from monasca_api.v3.common import utils
from monasca_api.v3.common import validation

LOG = log.getLogger(__name__)


DELEGATE_AUTHORIZED_ROLES = cfg.CONF.security.delegate_authorized_roles
POST_METRICS_AUTHORIZED_ROLES = (cfg.CONF.security.default_authorized_roles +
                                 cfg.CONF.security.agent_authorized_roles)
GET_METRICS_AUTHORIZED_ROLES = (cfg.CONF.security.default_authorized_roles +
                                cfg.CONF.security.read_only_authorized_roles)


class Metrics(object):
    def __init__(self):
        try:
            super(Metrics, self).__init__()
            self._region = cfg.CONF.region
            self._message_queue = simport.load(cfg.CONF.messaging.driver)(
                'metrics')
            self._metrics_repo = simport.load(
                cfg.CONF.repositories.metrics_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise falcon.HTTPInternalServerError('Service unavailable',
                                                 ex.message)

    def _send_metrics(self, metrics):
        try:
            self._message_queue.send_message(metrics)
        except message_queue_exceptions.MessageQueueException as ex:
            LOG.exception(ex)
            raise falcon.HTTPServiceUnavailable('Service unavailable',
                                                ex.message, 60)

    @utils.exception_translator
    @auth.Authorize(authorized_roles=POST_METRICS_AUTHORIZED_ROLES,
                    delegate_authorized_roles=DELEGATE_AUTHORIZED_ROLES)
    def on_post(self, req, res):
        utils.validate_json_content_type(req)
        msg = req.stream.read()
        metrics = simplejson.loads(msg)

        metric_validation.validate(metrics)

        transformed_metrics = metrics_message.transform(metrics, req.tenant_id, self._region)
        self._send_metrics(transformed_metrics)
        res.status = falcon.HTTP_204

    @utils.exception_translator
    @auth.Authorize(authorized_roles=GET_METRICS_AUTHORIZED_ROLES,
                    delegate_authorized_roles=DELEGATE_AUTHORIZED_ROLES)
    def on_get(self, req, response):
        name = req.get_param('name')
        dimensions = req.get_param_as_dimensions('dimensions')
        start_timestamp = req.get_param_as_datetime('start_time')
        end_timestamp = req.get_param_as_datetime('end_time')
        offset = req.get_param('offset')
        limit = req.limit

        validation.validate_metric_name(name)
        validation.validate_dimensions(dimensions)
        validation.validate_time_range(start_timestamp, end_timestamp)

        result = self._metrics_repo.list_metrics(req.tenant_id,
                                                 self._region,
                                                 name,
                                                 dimensions,
                                                 offset, limit,
                                                 start_timestamp,
                                                 end_timestamp)

        paginated_result = pagination.paginate(result, req.uri, limit)

        response.body = utils.dumps_json_utf8(paginated_result)
        response.status = falcon.HTTP_200


class MetricsMeasurements(object):
    def __init__(self):
        try:
            super(MetricsMeasurements, self).__init__()
            self._region = cfg.CONF.region
            self._metrics_repo = simport.load(
                cfg.CONF.repositories.metrics_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise falcon.HTTPInternalServerError('Service unavailable',
                                                 ex.message)

    @utils.exception_translator
    @auth.Authorize(authorized_roles=GET_METRICS_AUTHORIZED_ROLES,
                    delegate_authorized_roles=DELEGATE_AUTHORIZED_ROLES)
    def on_get(self, req, res):

        query_params = {}
        req.get_param('name', store=query_params, required=True)
        req.get_param_as_dimensions('dimensions', store=query_params)
        req.get_param_as_datetime('start_time', store=query_params, required=True)
        req.get_param_as_datetime('end_time', store=query_params)
        req.get_param_as_bool('merge_metrics', store=query_params)
        req.get_param_as_list('group_by', store=query_params, default=[])
        req.get_param('offset', store=query_params)
        limit = req.limit

        validation.validate_metric_name(query_params['name'])
        validation.validate_dimensions(query_params['dimensions'])
        validation.validate_time_range(query_params['start_time'], query_params['end_time'])

        result = self._metrics_repo.measurement_list(req.tenant_id,
                                                     self._region,
                                                     query_params['name'],
                                                     query_params['dimensions'],
                                                     query_params['start_time'],
                                                     query_params['end_time'],
                                                     query_params['offset'],
                                                     limit,
                                                     query_params['merge_metrics'],
                                                     query_params['group_by'])

        paginated_result = pagination.paginate_measurements(result, req.uri, limit)

        res.body = utils.dumps_json_utf8(paginated_result)
        res.status = falcon.HTTP_200


class MetricsStatistics(object):
    def __init__(self):
        try:
            super(MetricsStatistics, self).__init__()
            self._region = cfg.CONF.region
            self._metrics_repo = simport.load(
                cfg.CONF.repositories.metrics_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise falcon.HTTPInternalServerError('Service unavailable',
                                                 ex.message)

    @utils.exception_translator
    @auth.Authorize(authorized_roles=GET_METRICS_AUTHORIZED_ROLES,
                    delegate_authorized_roles=DELEGATE_AUTHORIZED_ROLES)
    def on_get(self, req, res):
        query_params = {}
        req.get_param('name', store=query_params, required=True)
        req.get_param_as_dimensions('dimensions', store=query_params)
        req.get_param_as_datetime('start_time', store=query_params, required=True)
        req.get_param_as_datetime('end_time', store=query_params)
        req.get_param_as_list('statistics', store=query_params, required=True)
        req.get_param_as_int('period', store=query_params, min=0, default=300)
        req.get_param('offset', store=query_params)
        req.get_param_as_bool('merge_metrics', store=query_params)
        req.get_param_as_list('group_by', store=query_params, default=[])
        limit = req.limit

        validation.validate_metric_name(query_params['name'])
        validation.validate_dimensions(query_params['dimensions'])
        validation.validate_time_range(query_params['start_time'], query_params['end_time'])
        validation.validate_statistics(query_params['statistics'])

        result = self._metrics_repo.metrics_statistics(req.tenant_id,
                                                       self._region,
                                                       query_params['name'],
                                                       query_params['dimensions'],
                                                       query_params['start_time'],
                                                       query_params['end_time'],
                                                       query_params['statistics'],
                                                       query_params['period'],
                                                       query_params['offset'],
                                                       limit,
                                                       query_params['merge_metrics'],
                                                       query_params['group_by'])

        paginated_result = pagination.paginate_statistics(result, req.uri, limit)

        res.body = utils.dumps_json_utf8(paginated_result)
        res.status = falcon.HTTP_200


class MetricsNames(object):
    def __init__(self):
        try:
            super(MetricsNames, self).__init__()
            self._region = cfg.CONF.region
            self._metrics_repo = simport.load(
                cfg.CONF.repositories.metrics_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise falcon.HTTPInternalServerError('Service unavailable',
                                                 ex.message)

    @utils.exception_translator
    @auth.Authorize(authorized_roles=GET_METRICS_AUTHORIZED_ROLES,
                    delegate_authorized_roles=DELEGATE_AUTHORIZED_ROLES)
    def on_get(self, req, res):
        dimensions = req.get_param_as_dimensions('dimensions')
        offset = req.get_param('offset')
        limit = req.limit

        validation.validate_dimensions(dimensions)

        result = self._metrics_repo.list_metric_names(req.tenant_id,
                                                      self._region,
                                                      dimensions)

        paginated_result = pagination.paginate_with_no_id(result, req.uri, offset, limit)

        res.body = utils.dumps_json_utf8(paginated_result)
        res.status = falcon.HTTP_200


class DimensionNames(object):
    def __init__(self):
        try:
            super(DimensionNames, self).__init__()
            self._region = cfg.CONF.region
            self._metrics_repo = simport.load(
                cfg.CONF.repositories.metrics_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise falcon.HTTPInternalServerError('Service unavailable',
                                                 ex.message)

    @utils.exception_translator
    @auth.Authorize(authorized_roles=GET_METRICS_AUTHORIZED_ROLES,
                    delegate_authorized_roles=DELEGATE_AUTHORIZED_ROLES)
    def on_get(self, req, res):
        metric_name = req.get_param('metric_name')
        offset = req.get_param('offset')
        limit = req.limit

        result = self._metrics_repo.list_dimension_names(req.tenant_id,
                                                         self._region,
                                                         metric_name)

        paginated_result = pagination.paginate_with_no_id(result, req.uri, offset, limit)

        res.body = utils.dumps_json_utf8(paginated_result)
        res.status = falcon.HTTP_200


class DimensionValues(object):
    def __init__(self):
        try:
            super(DimensionValues, self).__init__()
            self._region = cfg.CONF.region
            self._metrics_repo = simport.load(
                cfg.CONF.repositories.metrics_driver)()

        except Exception as ex:
            LOG.exception(ex)
            raise falcon.HTTPInternalServerError('Service unavailable',
                                                 ex.message)

    @utils.exception_translator
    @auth.Authorize(authorized_roles=GET_METRICS_AUTHORIZED_ROLES,
                    delegate_authorized_roles=DELEGATE_AUTHORIZED_ROLES)
    def on_get(self, req, res):
        metric_name = req.get_param('metric_name')
        dimension_name = req.get_param('dimension_name', required=True)
        offset = req.get_param('offset')
        limit = req.limit

        validation.validate_metric_name(metric_name)
        metric_validation.validate_dimension_key(dimension_name)

        result = self._metrics_repo.list_dimension_values(req.tenant_id,
                                                          self._region,
                                                          metric_name,
                                                          dimension_name)

        paginated_result = pagination.paginate_with_no_id(result, req.uri, offset, limit)

        res.body = utils.dumps_json_utf8(paginated_result)
        res.status = falcon.HTTP_200
