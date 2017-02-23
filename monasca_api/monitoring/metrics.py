# Copyright 2016 FUJITSU LIMITED
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

METRICS_REJECTED_COUNT = "api.metrics_rejected"
""" invalid metrics posted to API """
METRICS_PUBLISH_TIME = "api.metrics_publish_time"
""" time needed to send metric batch to Kafka """
METRICS_LIST_TIME = "api.metrics_list_time"
""" time needed to list all metrics """
METRICS_RETRIEVE_TIME = "api.metrics_retrieve_time"
""" time needed to load measurement data for a single metric """
METRICS_DIMS_RETRIEVE_TIME = "api.metrics_dims_retrieve_time"
""" time needed to retrieve known values for a dimension """
METRICS_STATS_TIME = "api.metrics_stats_time"
""" time needed to compute statistics for a single metric """
ALARMS_LIST_TIME = "api.alarms_list_time"
""" time needed to list alarms """

INFLUXDB_QUERY_TIME = "influxdb.query_time"
"""time needed to query data from InfluxDB """
TSDB_ERRORS = "tsdb.access_errors"
""" errors when accessing the TSDB (e.g. InfluxDB) """
CONFIGDB_ERRORS = "configdb.access_errors"
""" errors when accessing the configuration DB (e.g. MySQL) """
CONFIGDB_TIME = "configdb.access_time"
""" time needed to access the configuration DB (e.g. MySQL) """
KAFKA_PRODUCER_ERRORS = "kafka.producer_errors"
""" errors when publishing a message or message batch to Kafka """
