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


_XTRACE_MON_ELK=$(set +o | grep xtrace)
set +o xtrace

_ERREXIT_MON_ELK=$(set +o | grep errexit)
set -o errexit


function install_elk {
    if is_service_enabled monasca-log; then
        install_logstash
    fi
    if is_service_enabled monasca-log $$ moansca-events; then
        install_elasticsearch
        install_kibana
    fi
}


is_logstash_required() {
    is_service_enabled monasca-log-persister \
        || is_service_enabled monasca-log-transformer \
        || is_service_enabled monasca-log-metrics \
        || is_service_enabled monasca-log-agent \
        && return 0
}

function install_logstash {
    if is_logstash_required; then
        echo_summary "Installing Logstash ${LOGSTASH_VERSION}"

        local logstash_tarball=logstash-oss-${LOGSTASH_VERSION}.tar.gz
        local logstash_url=https://artifacts.elastic.co/downloads/logstash/${logstash_tarball}

        local logstash_dest
        logstash_dest=`get_extra_file ${logstash_url}`

        tar xzf ${logstash_dest} -C $DEST

        sudo chown -R $STACK_USER $DEST/logstash-${LOGSTASH_VERSION}
        ln -sf $DEST/logstash-${LOGSTASH_VERSION} $LOGSTASH_DIR

        sudo mkdir -p $LOGSTASH_DATA_DIR
        sudo chown $STACK_USER:monasca $LOGSTASH_DATA_DIR
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

        local es_tarball=elasticsearch-oss-${ELASTICSEARCH_VERSION}-linux-x86_64.tar.gz
        local es_url=https://artifacts.elastic.co/downloads/elasticsearch/${es_tarball}

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
            s|%ES_DATA_DIR%|$ELASTICSEARCH_DATA_DIR|g;
            s|%ES_LOG_DIR%|$ELASTICSEARCH_LOG_DIR|g;
        " -i $ELASTICSEARCH_CFG_DIR/elasticsearch.yml

        ln -sf $ELASTICSEARCH_CFG_DIR/elasticsearch.yml $GATE_CONFIGURATION_DIR/elasticsearch.yml

        echo "[Service]" | sudo tee --append /etc/systemd/system/devstack\@elasticsearch.service > /dev/null
        echo "LimitNOFILE=$LIMIT_NOFILE" | sudo tee --append /etc/systemd/system/devstack\@elasticsearch.service > /dev/null

        echo "vm.max_map_count=$VM_MAX_MAP_COUNT" | sudo tee --append /etc/sysctl.conf > /dev/null
        sudo sysctl -w vm.max_map_count=$VM_MAX_MAP_COUNT
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

        local kibana_tarball=kibana-oss-${KIBANA_VERSION}.tar.gz
        local kibana_tarball_url=https://artifacts.elastic.co/downloads/kibana/${kibana_tarball}
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
            s|%ES_SERVICE_BIND_HOST%|$ES_SERVICE_BIND_HOST|g;
            s|%ES_SERVICE_BIND_PORT%|$ES_SERVICE_BIND_PORT|g;
            s|%KIBANA_SERVER_BASE_PATH%|$KIBANA_SERVER_BASE_PATH|g;
            s|%KEYSTONE_AUTH_URI%|$KEYSTONE_AUTH_URI|g;
        " -i $KIBANA_CFG_DIR/kibana.yml

        ln -sf $KIBANA_CFG_DIR/kibana.yml $GATE_CONFIGURATION_DIR/kibana.yml
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
        local kibanaSleepTime=${KIBANA_SLEEP_TIME:-120}     # kibana takes some time to load up
        local kibanaCFG="$KIBANA_CFG_DIR/kibana.yml"
        run_process_sleep "kibana" "$KIBANA_DIR/bin/kibana --config $kibanaCFG" $kibanaSleepTime
    fi
}

function create_default_index_pattern {
    local tenant_id
    tenant_id=`get_or_create_project "mini-mon"`
    local index_pattern="logs-$tenant_id*"

    curl -XPOST "$KIBANA_SERVICE_HOST:$KIBANA_SERVICE_PORT/api/saved_objects/index-pattern/$index_pattern" \
        -H 'kbn-xsrf: true' -H "Content-Type: application/json" -d '{"attributes":{"title":"'$index_pattern'", "timeFieldName": "@timestamp"}}'
    curl -X GET "$KIBANA_SERVICE_HOST:$KIBANA_SERVICE_PORT/api/saved_objects/index-pattern/$index_pattern" -H 'kbn-xsrf: true'
}


#Restore errexit
${_ERREXIT_MON_ELK}

# Restore xtrace
${_XTRACE_MON_ELK}
