#!/usr/bin/env bash
#
# Copyright 2020 FUJITSU LIMITED
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

_XTRACE_MON_EVENTS=$(set +o | grep xtrace)
set +o xtrace

_ERREXIT_MON_EVENTS=$(set +o | grep errexit)
set -o errexit


function configure_monasca-events {
    configure_kafka


}
function configure_kafka {
    echo_summary "Configuring Kafka topics"
    /opt/kafka/bin/kafka-topics.sh --create --zookeeper localhost:2181 \
        --replication-factor 1 --partitions 3 --topic openstack-events
}

function delete_kafka_topics {
    echo_summary "Deleting Kafka topics"
        /opt/kafka/bin/kafka-topics.sh --delete --zookeeper localhost:2181 \
                --topic evetns || true
}

function create_events_management_accounts {
    echo_summary "Enable events Management in Keystone"

    get_or_create_service "events" "events" "Monasca Events service"
    get_or_create_endpoint \
        "logs" \
        "$REGION_NAME" \
        "$MONASCA_API_URI_V2" \
        "$MONASCA_API_URI_V2" \
        "$MONASCA_API_URI_V2"
}

#Restore errexit
${_ERREXIT_MON_EVENTS}

# Restore xtrace
${_XTRACE_MON_EVENTS}
