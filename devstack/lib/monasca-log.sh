#!/bin/bash

#
# Copyright 2016-2017 FUJITSU LIMITED
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

_XTRACE_MON_LOG=$(set +o | grep xtrace)
set +o xtrace

_ERREXIT_MON_LOG=$(set +o | grep errexit)
set -o errexit

# configuration bits of various services
LOG_PERSISTER_DIR=$DEST/monasca-log-persister
LOG_TRANSFORMER_DIR=$DEST/monasca-log-transformer
LOG_METRICS_DIR=$DEST/monasca-log-metrics
LOG_AGENT_DIR=$DEST/monasca-log-agent

ELASTICSEARCH_DIR=$DEST/elasticsearch
ELASTICSEARCH_CFG_DIR=$ELASTICSEARCH_DIR/config
ELASTICSEARCH_LOG_DIR=$LOGDIR/elasticsearch
ELASTICSEARCH_DATA_DIR=$DATA_DIR/elasticsearch

KIBANA_DIR=$DEST/kibana
KIBANA_CFG_DIR=$KIBANA_DIR/config

LOGSTASH_DIR=$DEST/logstash


ES_SERVICE_BIND_HOST=${ES_SERVICE_BIND_HOST:-${SERVICE_HOST}}
ES_SERVICE_BIND_PORT=${ES_SERVICE_BIND_PORT:-9200}
ES_SERVICE_PUBLISH_HOST=${ES_SERVICE_PUBLISH_HOST:-${SERVICE_HOST}}
ES_SERVICE_PUBLISH_PORT=${ES_SERVICE_PUBLISH_PORT:-9300}

KIBANA_SERVICE_HOST=${KIBANA_SERVICE_HOST:-${SERVICE_HOST}}
KIBANA_SERVICE_PORT=${KIBANA_SERVICE_PORT:-5601}
KIBANA_SERVER_BASE_PATH=${KIBANA_SERVER_BASE_PATH:-"/dashboard/monitoring/logs_proxy"}


run_process_sleep() {
    local name=$1
    local cmd=$2
    local sleepTime=${3:-1}
    run_process "$name" "$cmd"
    sleep ${sleepTime}
}

is_logstash_required() {
    is_service_enabled monasca-log-persister \
        || is_service_enabled monasca-log-transformer \
        || is_service_enabled monasca-log-metrics \
        || is_service_enabled monasca-log-agent \
        && return 0
}

# TOP_LEVEL functions called from devstack coordinator
###############################################################################
function pre_install_logs_services {
    install_elk
    install_nodejs
    install_gate_config_holder
}

function install_monasca_log {
    build_kibana_plugin
    install_log_agent
}

function install_elk {
    install_logstash
    install_elasticsearch
    install_kibana
}

function install_gate_config_holder {
    sudo install -d -o $STACK_USER $GATE_CONFIGURATION_DIR
}

function install_monasca_statsd {
    if use_library_from_git "monasca-statsd"; then
        git_clone_by_name "monasca-statsd"
        setup_dev_lib "monasca-statsd"
    fi
}

function configure_monasca_log {
    configure_kafka
    configure_elasticsearch
    configure_kibana
    install_kibana_plugin
    configure_monasca_log_api
    configure_monasca_log_transformer
    configure_monasca_log_metrics
    configure_monasca_log_persister
    configure_monasca_log_agent
}

function init_monasca_log {
    enable_log_management
}

function init_monasca_grafana_dashboards {
    if is_service_enabled horizon; then
        echo_summary "Init Grafana dashboards"

        sudo python "${PLUGIN_FILES}"/grafana/grafana.py "${PLUGIN_FILES}"/grafana/dashboards.d
    fi
}

function init_agent {
    echo_summary "Init Monasca agent"

    sudo cp -f "${PLUGIN_FILES}"/monasca-agent/http_check.yaml /etc/monasca/agent/conf.d/http_check.yaml
    sudo cp -f "${PLUGIN_FILES}"/monasca-agent/process.yaml /etc/monasca/agent/conf.d/process.yaml
    sudo cp -f "${PLUGIN_FILES}"/monasca-agent/elastic.yaml /etc/monasca/agent/conf.d/elastic.yaml

    sudo sed -i "s/{{IP}}/$(ip -o -4 addr list eth1 | awk '{print $4}' | cut -d/ -f1 | head -1)/" /etc/monasca/agent/conf.d/*.yaml
    sudo sed -i "s/127\.0\.0\.1/$(hostname)/" /etc/monasca/agent/conf.d/*.yaml
    sudo systemctl restart monasca-collector
}

function stop_monasca_log {
    stop_process "monasca-log-agent" || true
    stop_monasca_log_api
    stop_process "monasca-log-metrics" || true
    stop_process "monasca-log-persister" || true
    stop_process "monasca-log-transformer" || true
    stop_process "kibana" || true
    stop_process "elasticsearch" || true
}

function start_monasca_log {
    start_elasticsearch
    start_kibana
    start_monasca_log_transformer
    start_monasca_log_metrics
    start_monasca_log_persister
    start_monasca_log_api
    start_monasca_log_agent
}

function clean_monasca_log {
    clean_monasca_log_agent
    clean_monasca_log_api
    clean_monasca_log_persister
    clean_monasca_log_transformer
    clean_kibana
    clean_elasticsearch
    clean_logstash
    clean_nodejs
    clean_gate_config_holder
}
###############################################################################

function configure_monasca_log_api {
    if is_service_enabled monasca-api; then
        echo_summary "Configuring monasca-api"
        iniset "$MONASCA_API_CONF" DEFAULT enable_logs_api "true"
        iniset "$MONASCA_API_CONF" kafka logs_topics "log"

        create_log_management_accounts
    fi
}

function install_logstash {
    if is_logstash_required; then
        echo_summary "Installing Logstash ${LOGSTASH_VERSION}"

        local logstash_tarball=logstash-${LOGSTASH_VERSION}.tar.gz
        local logstash_url=http://download.elastic.co/logstash/logstash/${logstash_tarball}

        local logstash_dest
        logstash_dest=`get_extra_file ${logstash_url}`

        tar xzf ${logstash_dest} -C $DEST

        sudo chown -R $STACK_USER $DEST/logstash-${LOGSTASH_VERSION}
        ln -sf $DEST/logstash-${LOGSTASH_VERSION} $LOGSTASH_DIR
    fi
}

function clean_logstash {
    if is_logstash_required; then
        echo_summary "Cleaning Logstash ${LOGSTASH_VERSION}"

        sudo rm -rf $LOGSTASH_DIR || true
        sudo rm -rf $FILES/logstash-${LOGSTASH_VERSION}.tar.gz ||  true
        sudo rm -rf $DEST/logstash-${LOGSTASH_VERSION} || true
    fi
}

function install_elasticsearch {
    if is_service_enabled elasticsearch; then
        echo_summary "Installing ElasticSearch ${ELASTICSEARCH_VERSION}"

        local es_tarball=elasticsearch-${ELASTICSEARCH_VERSION}.tar.gz
        local es_url=https://download.elastic.co/elasticsearch/release/org/elasticsearch/distribution/tar/elasticsearch/${ELASTICSEARCH_VERSION}/${es_tarball}

        local es_dest
        es_dest=`get_extra_file ${es_url}`

        tar xzf ${es_dest} -C $DEST

        sudo chown -R $STACK_USER $DEST/elasticsearch-${ELASTICSEARCH_VERSION}
        ln -sf $DEST/elasticsearch-${ELASTICSEARCH_VERSION} $ELASTICSEARCH_DIR
    fi
}

function configure_elasticsearch {
    if is_service_enabled elasticsearch; then
        echo_summary "Configuring ElasticSearch ${ELASTICSEARCH_VERSION}"

        local templateDir=$ELASTICSEARCH_CFG_DIR/templates

        for dir in $ELASTICSEARCH_LOG_DIR $templateDir $ELASTICSEARCH_DATA_DIR; do
            sudo install -m 755 -d -o $STACK_USER $dir
        done

        sudo cp -f "${PLUGIN_FILES}"/elasticsearch/elasticsearch.yml $ELASTICSEARCH_CFG_DIR/elasticsearch.yml
        sudo chown -R $STACK_USER $ELASTICSEARCH_CFG_DIR/elasticsearch.yml
        sudo chmod 0644 $ELASTICSEARCH_CFG_DIR/elasticsearch.yml

        sudo sed -e "
            s|%ES_SERVICE_BIND_HOST%|$ES_SERVICE_BIND_HOST|g;
            s|%ES_SERVICE_BIND_PORT%|$ES_SERVICE_BIND_PORT|g;
            s|%ES_SERVICE_PUBLISH_HOST%|$ES_SERVICE_PUBLISH_HOST|g;
            s|%ES_SERVICE_PUBLISH_PORT%|$ES_SERVICE_PUBLISH_PORT|g;
            s|%ES_DATA_DIR%|$ELASTICSEARCH_DATA_DIR|g;
            s|%ES_LOG_DIR%|$ELASTICSEARCH_LOG_DIR|g;
        " -i $ELASTICSEARCH_CFG_DIR/elasticsearch.yml

        ln -sf $ELASTICSEARCH_CFG_DIR/elasticsearch.yml $GATE_CONFIGURATION_DIR/elasticsearch.yml
    fi
}

function clean_elasticsearch {
    if is_service_enabled elasticsearch; then
        echo_summary "Cleaning Elasticsearch ${ELASTICSEARCH_VERSION}"

        sudo rm -rf ELASTICSEARCH_DIR || true
        sudo rm -rf ELASTICSEARCH_CFG_DIR || true
        sudo rm -rf ELASTICSEARCH_LOG_DIR || true
        sudo rm -rf ELASTICSEARCH_DATA_DIR || true
        sudo rm -rf $FILES/elasticsearch-${ELASTICSEARCH_VERSION}.tar.gz || true
        sudo rm -rf $DEST/elasticsearch-${ELASTICSEARCH_VERSION} || true
    fi
}

function start_elasticsearch {
    if is_service_enabled elasticsearch; then
        echo_summary "Starting ElasticSearch ${ELASTICSEARCH_VERSION}"
        # 5 extra seconds to ensure that ES started properly
        local esSleepTime=${ELASTICSEARCH_SLEEP_TIME:-5}
        run_process_sleep "elasticsearch" "$ELASTICSEARCH_DIR/bin/elasticsearch" $esSleepTime
    fi
}

function install_kibana {
    if is_service_enabled kibana; then
        echo_summary "Installing Kibana ${KIBANA_VERSION}"

        local kibana_tarball=kibana-${KIBANA_VERSION}.tar.gz
        local kibana_tarball_url=http://download.elastic.co/kibana/kibana/${kibana_tarball}

        local kibana_tarball_dest
        kibana_tarball_dest=`get_extra_file ${kibana_tarball_url}`

        tar xzf ${kibana_tarball_dest} -C $DEST

        sudo chown -R $STACK_USER $DEST/kibana-${KIBANA_VERSION}
        ln -sf $DEST/kibana-${KIBANA_VERSION} $KIBANA_DIR
    fi
}

function configure_kibana {
    if is_service_enabled kibana; then
        echo_summary "Configuring Kibana ${KIBANA_VERSION}"

        sudo install -m 755 -d -o $STACK_USER $KIBANA_CFG_DIR

        sudo cp -f "${PLUGIN_FILES}"/kibana/kibana.yml $KIBANA_CFG_DIR/kibana.yml
        sudo chown -R $STACK_USER $KIBANA_CFG_DIR/kibana.yml
        sudo chmod 0644 $KIBANA_CFG_DIR/kibana.yml

        sudo sed -e "
            s|%KIBANA_SERVICE_HOST%|$KIBANA_SERVICE_HOST|g;
            s|%KIBANA_SERVICE_PORT%|$KIBANA_SERVICE_PORT|g;
            s|%KIBANA_SERVER_BASE_PATH%|$KIBANA_SERVER_BASE_PATH|g;
            s|%ES_SERVICE_BIND_HOST%|$ES_SERVICE_BIND_HOST|g;
            s|%ES_SERVICE_BIND_PORT%|$ES_SERVICE_BIND_PORT|g;
            s|%KEYSTONE_AUTH_URI%|$KEYSTONE_AUTH_URI|g;
        " -i $KIBANA_CFG_DIR/kibana.yml

        ln -sf $KIBANA_CFG_DIR/kibana.yml $GATE_CONFIGURATION_DIR/kibana.yml
    fi
}

function install_kibana_plugin {
    if is_service_enabled kibana; then
        echo_summary "Install Kibana plugin"

        # note(trebskit) that needs to happen after kibana received
        # its configuration otherwise the plugin fails to be installed

        local pkg=file://$DEST/monasca-kibana-plugin.tar.gz

        $KIBANA_DIR/bin/kibana plugin -r monasca-kibana-plugin
        $KIBANA_DIR/bin/kibana plugin -i monasca-kibana-plugin -u $pkg
    fi
}

function clean_kibana {
    if is_service_enabled kibana; then
        echo_summary "Cleaning Kibana ${KIBANA_VERSION}"

        sudo rm -rf $KIBANA_DIR || true
        sudo rm -rf $FILES/kibana-${KIBANA_VERSION}.tar.gz || true
        sudo rm -rf $KIBANA_CFG_DIR || true
    fi
}

function start_kibana {
    if is_service_enabled kibana; then
        echo_summary "Starting Kibana ${KIBANA_VERSION}"
        local kibanaSleepTime=${KIBANA_SLEEP_TIME:-90}     # kibana takes some time to load up
        local kibanaCFG="$KIBANA_CFG_DIR/kibana.yml"
        run_process_sleep "kibana" "$KIBANA_DIR/bin/kibana --config $kibanaCFG" $kibanaSleepTime
    fi
}

function configure_monasca_log_persister {
    if is_service_enabled monasca-log-persister; then
        echo_summary "Configuring monasca-log-persister"

        sudo install -m 755 -d -o $STACK_USER $LOG_PERSISTER_DIR

        sudo cp -f "${PLUGIN_FILES}"/monasca-log-persister/persister.conf $LOG_PERSISTER_DIR/persister.conf
        sudo chown $STACK_USER $LOG_PERSISTER_DIR/persister.conf
        sudo chmod 0640 $LOG_PERSISTER_DIR/persister.conf

        sudo sed -e "
            s|%ES_SERVICE_BIND_HOST%|$ES_SERVICE_BIND_HOST|g;
        " -i $LOG_PERSISTER_DIR/persister.conf

        ln -sf $LOG_PERSISTER_DIR/persister.conf $GATE_CONFIGURATION_DIR/log-persister.conf
    fi
}

function clean_monasca_log_persister {
    if is_service_enabled monasca-log-persister; then
        echo_summary "Cleaning monasca-log-persister"
        sudo rm -rf $LOG_PERSISTER_DIR || true
    fi
}

function start_monasca_log_persister {
    if is_service_enabled monasca-log-persister; then
        echo_summary "Starting monasca-log-persister"
        local logstash="$LOGSTASH_DIR/bin/logstash"
        run_process "monasca-log-persister" "$logstash -f $LOG_PERSISTER_DIR/persister.conf"
    fi
}

function configure_monasca_log_transformer {
    if is_service_enabled monasca-log-transformer; then
        echo_summary "Configuring monasca-log-transformer"

        sudo install -m 755 -d -o $STACK_USER $LOG_TRANSFORMER_DIR

        sudo cp -f "${PLUGIN_FILES}"/monasca-log-transformer/transformer.conf $LOG_TRANSFORMER_DIR/transformer.conf
        sudo chown $STACK_USER $LOG_TRANSFORMER_DIR/transformer.conf
        sudo chmod 0640 $LOG_TRANSFORMER_DIR/transformer.conf

        sudo sed -e "
            s|%KAFKA_SERVICE_HOST%|$KAFKA_SERVICE_HOST|g;
            s|%KAFKA_SERVICE_PORT%|$KAFKA_SERVICE_PORT|g;
        " -i $LOG_TRANSFORMER_DIR/transformer.conf

        ln -sf $LOG_TRANSFORMER_DIR/transformer.conf $GATE_CONFIGURATION_DIR/log-transformer.conf
    fi
}

function clean_monasca_log_transformer {
    if is_service_enabled monasca-log-transformer; then
        echo_summary "Cleaning monasca-log-transformer"
        sudo rm -rf $LOG_TRANSFORMER_DIR || true
    fi
}

function start_monasca_log_transformer {
    if is_service_enabled monasca-log-transformer; then
        echo_summary "Starting monasca-log-transformer"
        local logstash="$LOGSTASH_DIR/bin/logstash"
        run_process "monasca-log-transformer" "$logstash -f $LOG_TRANSFORMER_DIR/transformer.conf"
    fi
}

function configure_monasca_log_metrics {
    if is_service_enabled monasca-log-metrics; then
        echo_summary "Configuring monasca-log-metrics"

        sudo install -m 755 -d -o $STACK_USER $LOG_METRICS_DIR

        sudo cp -f "${PLUGIN_FILES}"/monasca-log-metrics/log-metrics.conf $LOG_METRICS_DIR/log-metrics.conf
        sudo chown $STACK_USER $LOG_METRICS_DIR/log-metrics.conf
        sudo chmod 0640 $LOG_METRICS_DIR/log-metrics.conf

        sudo sed -e "
            s|%KAFKA_SERVICE_HOST%|$KAFKA_SERVICE_HOST|g;
            s|%KAFKA_SERVICE_PORT%|$KAFKA_SERVICE_PORT|g;
        " -i $LOG_METRICS_DIR/log-metrics.conf

        ln -sf $LOG_METRICS_DIR/log-metrics.conf $GATE_CONFIGURATION_DIR/log-metrics.conf
    fi
}

function clean_monasca_log_metrics {
    if is_service_enabled monasca-log-metrics; then
        echo_summary "Cleaning monasca-log-metrics"
        sudo rm -rf $LOG_METRICS_DIR || true
    fi
}

function start_monasca_log_metrics {
    if is_service_enabled monasca-log-metrics; then
        echo_summary "Starting monasca-log-metrics"
        local logstash="$LOGSTASH_DIR/bin/logstash"
        run_process "monasca-log-metrics" "$logstash -f $LOG_METRICS_DIR/log-metrics.conf"
    fi
}

function install_log_agent {
    if is_service_enabled monasca-log-agent; then
        echo_summary "Installing monasca-log-agent [monasca-output-plugin]"

        $LOGSTASH_DIR/bin/plugin install --version \
            "${LOGSTASH_OUTPUT_MONASCA_VERSION}" logstash-output-monasca_log_api
    fi
}

function configure_monasca_log_agent {
    if is_service_enabled monasca-log-agent; then
        echo_summary "Configuring monasca-log-agent"

        sudo install -m 755 -d -o $STACK_USER $LOG_AGENT_DIR

        sudo cp -f "${PLUGIN_FILES}"/monasca-log-agent/agent.conf $LOG_AGENT_DIR/agent.conf
        sudo chown $STACK_USER $LOG_AGENT_DIR/agent.conf
        sudo chmod 0640 $LOG_AGENT_DIR/agent.conf

        sudo sed -e "
            s|%MONASCA_LOG_API_URI_V3%|$MONASCA_LOG_API_URI_V3|g;
            s|%KEYSTONE_AUTH_URI_V3%|$KEYSTONE_AUTH_URI_V3|g;
        " -i $LOG_AGENT_DIR/agent.conf

        ln -sf $LOG_AGENT_DIR/agent.conf $GATE_CONFIGURATION_DIR/log-agent.conf

    fi
}

function clean_monasca_log_agent {
    if is_service_enabled monasca-log-agent; then
        echo_summary "Cleaning monasca-log-agent"
        sudo rm -rf $LOG_AGENT_DIR || true
    fi
}

function start_monasca_log_agent {
    if is_service_enabled monasca-log-agent; then
        echo_summary "Starting monasca-log-agent"
        local logstash="$LOGSTASH_DIR/bin/logstash"
        run_process "monasca-log-agent" "$logstash -f $LOG_AGENT_DIR/agent.conf" "root" "root"
    fi
}

function install_nodejs {
    if is_service_enabled kibana; then
        # refresh installation
        apt_get install nodejs npm
        (
            npm config set registry "http://registry.npmjs.org/"; \
            npm config set proxy "${HTTP_PROXY}"; \
            npm set strict-ssl false;
        )
    fi
}

function clean_nodejs {
    if is_service_enabled kibana; then
        echo_summary "Cleaning Node.js"
        apt_get purge nodejs npm
    fi
}

function clean_gate_config_holder {
    sudo rm -rf $GATE_CONFIGURATION_DIR || true
}

function build_kibana_plugin {
    if is_service_enabled kibana; then
        echo "Building Kibana plugin"

        git_clone $MONASCA_KIBANA_PLUGIN_REPO $MONASCA_KIBANA_PLUGIN_DIR \
            $MONASCA_KIBANA_PLUGIN_BRANCH

        pushd $MONASCA_KIBANA_PLUGIN_DIR

        local monasca_kibana_plugin_version
        monasca_kibana_plugin_version="$(python -c 'import json; \
            obj = json.load(open("package.json")); print obj["version"]')"

        npm install
        npm run package

        local pkg=$MONASCA_KIBANA_PLUGIN_DIR/target/monasca-kibana-plugin-${monasca_kibana_plugin_version}.tar.gz
        local easyPkg=$DEST/monasca-kibana-plugin.tar.gz

        ln -sf $pkg $easyPkg

        popd
    fi
}

function configure_kafka {
    echo_summary "Configuring Kafka topics"
    /opt/kafka/bin/kafka-topics.sh --create --zookeeper localhost:2181 \
        --replication-factor 1 --partitions 4 --topic log
    /opt/kafka/bin/kafka-topics.sh --create --zookeeper localhost:2181 \
        --replication-factor 1 --partitions 4 --topic transformed-log
}

function delete_kafka_topics {
    echo_summary "Deleting Kafka topics"
        /opt/kafka/bin/kafka-topics.sh --delete --zookeeper localhost:2181 \
                --topic log || true
        /opt/kafka/bin/kafka-topics.sh --delete --zookeeper localhost:2181 \
                --topic transformed-log || true
}

function create_log_management_accounts {
    if is_service_enabled monasca-log && is_service_enabled momonasca-api; then
        echo_summary "Enable Log Management in Keystone"

        # note(trebskit) following points to Kibana which is bad,
        # but we do not have search-api in monasca-log-api now
        # this code will be removed in future
        local log_search_url="http://$KIBANA_SERVICE_HOST:$KIBANA_SERVICE_PORT/"

        get_or_create_service "logs" "logs" "Monasca Log service"
        get_or_create_endpoint \
            "logs" \
            "$REGION_NAME" \
            "$MONASCA_API_URI_V2" \
            "$MONASCA_API_URI_V2" \
            "$MONASCA_API_URI_V2"

        get_or_create_service "logs-search" "logs-search" "Monasca Log search service"
        get_or_create_endpoint \
            "logs-search" \
            "$REGION_NAME" \
            "$log_search_url" \
            "$log_search_url" \
            "$log_search_url"

    fi
}

function enable_log_management {
    if is_service_enabled horizon && is_service_enabled kibana; then
        echo_summary "Configure Horizon with Kibana access"

        local localSettings=${DEST}/horizon/monitoring/config/local_settings.py

        sudo sed -e "
            s|KIBANA_HOST = getattr(settings, 'KIBANA_HOST', 'http://192.168.10.4:5601/')|KIBANA_HOST = getattr(settings, 'KIBANA_HOST', 'http://${KIBANA_SERVICE_HOST}:${KIBANA_SERVICE_PORT}/')|g;
        " -i ${localSettings}

        if is_service_enabled monasca-log-api; then
            sudo sed -e "
                s|'ENABLE_LOG_MANAGEMENT_BUTTON', False|'ENABLE_LOG_MANAGEMENT_BUTTON', True|g;
            " -i ${localSettings}
        fi

        restart_apache_server
    fi
}

#Restore errexit
${_ERREXIT_MON_LOG}

# Restore xtrace
${_XTRACE_MON_LOG}