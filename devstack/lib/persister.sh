#!/bin/bash

# Copyright 2017 FUJITSU LIMITED
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless reqmonasca_PERSISTERred by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

_XTRACE_MON_PERSISTER=$(set +o | grep xtrace)
set +o xtrace

MONASCA_PERSISTER_IMPLEMENTATION_LANG=${MONASCA_PERSISTER_IMPLEMENTATION_LANG:-python}
MONASCA_PERSISTER_CONF_DIR=${MONASCA_PERSISTER_CONF_DIR:-/etc/monasca}
MONASCA_PERSISTER_LOG_DIR=${MONASCA_PERSISTER_LOG_DIR:-/var/log/monasca/persister}

if [ "$MONASCA_PERSISTER_IMPLEMENTATION_LANG" == "python" ]; then
    if [[ ${USE_VENV} = True ]]; then
        PROJECT_VENV["monasca-api"]=${MONASCA_API_DIR}.venv
        MONASCA_API_BIN_DIR=${PROJECT_VENV["monasca-api"]}/bin
    else
        MONASCA_API_BIN_DIR=$(get_python_exec_prefix)
    fi
    MONASCA_PERSISTER_CONF=${MONASCA_PERSISTER_CONF:-$MONASCA_PERSISTER_CONF_DIR/persister.conf}
    MONASCA_PERSISTER_LOGGING_CONF=${MONASCA_PERSISTER_LOGGING_CONF:-$MONASCA_PERSISTER_CONF_DIR/persister-logging.conf}

    M_REPO_DRIVER_BASE=monasca_persister.repositories.$MONASCA_METRICS_DB.metrics_repository
    M_REPO_DRIVER_INFLUX=$M_REPO_DRIVER_BASE:MetricInfluxdbRepository
    M_REPO_DRIVER_CASSANDRA=$M_REPO_DRIVER_BASE:MetricCassandraRepository

    AH_REPO_DRIVER_BASE=monasca_persister.repositories.$MONASCA_METRICS_DB.alarm_state_history_repository
    AH_REPO_DRIVER_INFLUX=$M_REPO_DRIVER_BASE:AlarmStateHistInfluxdbRepository
    AH_REPO_DRIVER_CASSANDRA=$M_REPO_DRIVER_BASE:AlarmStateHistCassandraRepository

else
    MONASCA_PERSISTER_CONF=${MONASCA_PERSISTER_CONF:-$MONASCA_PERSISTER_CONF_DIR/persister.yaml}
fi

is_monasca_persister_enabled() {
    is_service_enabled monasca-notification && return 0
    return 1
}

# common
install_monasca-persister() {
    echo_summary "Installing monasca-persister"

    git_clone ${MONASCA_PERSISTER_REPO} ${MONASCA_PERSISTER_DIR} \
        ${MONASCA_PERSISTER_BRANCH}

    install_monasca_persister_$MONASCA_PERSISTER_IMPLEMENTATION_LANG
}
configure_monasca-persister() {
  if ! is_monasca_persister_enabled; then
        return
    fi

    echo_summary "Configuring monasca-persister"

    sudo install -d -o $STACK_USER ${MONASCA_PERSISTER_CONF_DIR}
    sudo install -d -o $STACK_USER ${MONASCA_PERSISTER_LOG_DIR}

    configure_monasca_persister_$MONASCA_PERSISTER_IMPLEMENTATION_LANG
}
start_monasca-persister() {
    if ! is_monasca_persister_enabled; then
        return
    fi
    echo_summary "Starting monasca-persister"
    start_monasca_persister_$MONASCA_PERSISTER_IMPLEMENTATION_LANG
}
stop_monasca-persister() {
    if ! is_monasca_persister_enabled; then
        return
    fi
    echo_summary "Stopping monasca-persister"
    stop_monasca_persister_$MONASCA_PERSISTER_IMPLEMENTATION_LANG
}
clean_monasca-persister() {
    if ! is_monasca_persister_enabled; then
        return
    fi
    echo_summary "Cleaning monasca-persister"
    clean_monasca_persister_$MONASCA_PERSISTER_IMPLEMENTATION_LANG
}
# common

# python
install_monasca_persister_python() {
    setup_develop ${MONASCA_PERSISTER_DIR}

    install_monasca_common
    if [[ "${MONASCA_METRICS_DB,,}" == 'influxdb' ]]; then
        pip_install_gr influxdb
    elif [[ "${MONASCA_METRICS_DB,,}" == 'cassandra' ]]; then
        pip_install_gr cassandra-driver
    fi
}

configure_monasca_persister_python() {
    # ensure fresh installation of configuration files
    rm -rf $MONASCA_PERSISTER_CONF $MONASCA_PERSISTER_LOGGING_CONF

    install -m 600 $MONASCA_PERSISTER_DIR/etc/monasca/persister.conf $MONASCA_PERSISTER_CONF
    install -m 600 $MONASCA_PERSISTER_DIR/etc/monasca/persister-logging.conf $MONASCA_PERSISTER_LOGGING_CONF

    iniset "$MONASCA_PERSISTER_CONF" DEFAULT log_config_append $MONASCA_PERSISTER_LOGGING_CONF

    iniset "$MONASCA_PERSISTER_CONF" zookeeper uri $MONASCA_PERSISTER_LOGGING_CONF
    iniset "$MONASCA_PERSISTER_CONF" kafka_alarm_history uri $SERVICE_HOST:9092
    iniset "$MONASCA_PERSISTER_CONF" kafka_metrics uri $SERVICE_HOST:9092

    if [[ "${MONASCA_METRICS_DB,,}" == 'influxdb' ]]; then
        iniset "$MONASCA_PERSISTER_CONF" influxdb ip_address $SERVICE_HOST
        iniset "$MONASCA_PERSISTER_CONF" repositories metrics_driver $M_REPO_DRIVER_INFLUX
        iniset "$MONASCA_PERSISTER_CONF" repositories alarm_state_history_drive $M_REPO_DRIVER_CASSANDRA
    else
        iniset "$MONASCA_PERSISTER_CONF" cassandra cluster_ip_addresses $SERVICE_HOST
        iniset "$MONASCA_PERSISTER_CONF" cassandra keyspace monasca
        iniset "$MONASCA_PERSISTER_CONF" repositories metrics_driver $AH_REPO_DRIVER_INFLUX
        iniset "$MONASCA_PERSISTER_CONF" repositories alarm_state_history_drive $AH_REPO_DRIVER_CASSANDRA
    fi
}

start_monasca_persister_python() {
    if ! is_monasca_persister_enabled; then
        return
    fi
    run_process "monasca-persister" "$MONASCA_PERSISTER_BIN_DIR/monasca-persister --config-file=$MONASCA_PERSISTER_CONF"
}

stop_monasca_persister_python() {
    if ! is_monasca_persister_enabled; then
        return
    fi
    stop_process "monasca-persister"
}

clean_monasca_persister_python() {
    if ! is_monasca_persister_enabled; then
        return
    fi
}

# python

# java
install_monasca_persister_java() {
    (cd "${MONASCA_PERSISTER_DIR}"/java ; sudo mvn clean package -DskipTests)

    local version=""
    version="$(get_version_from_pom "${MONASCA_PERSISTER_DIR}"/java)"
    sudo cp -f "${MONASCA_PERSISTER_DIR}"/java/target/monasca-persister-${version}-shaded.jar \
        /opt/monasca/monasca-persister.jar

    sudo systemctl enable monasca-persister
}

configure_monasca_persister_java() {
    # ensure fresh installation of configuration file
    rm -rf $MONASCA_PERSISTER_CONF
}

start_monasca_persister_java() {
    start_service monasca-persister || restart_service monasca-persister
}

stop_monasca_persister_java() {
    stop_service monasca-persister
}
# java

${_XTRACE_MON_PERSISTER}
