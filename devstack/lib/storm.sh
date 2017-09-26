#!/bin/bash

# Copyright 2017 FUJITSU LIMITED
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

# call_order:
# - is_storm_enabled
# - install_storm
# - configure_storm
# - clean_storm

_XTRACE_STORM=$(set +o | grep xtrace)
set +o xtrace

STORM_NIMBUS_CMD="/opt/storm/current/bin/storm nimbus"
STORM_SUPERVISOR_CMD="/opt/storm/current/bin/storm supervisor"

STORM_USER="storm"
STORM_GROUP="storm"

STORM_DIR="/opt/storm"
STORM_CURRENT_DIR="${STORM_DIR}/current"
STORM_BIN="${STORM_CURRENT_DIR}/bin/storm"
STORM_WORK_DIR="/var/storm"
STORM_LOG_DIR="/var/log/storm"

STORM_TARBALL="apache-storm-${STORM_VERSION}.tar.gz"
STORM_TARBALL_DEST="${FILES}/${STORM_TARBALL}"

function is_storm_enabled {
    [[ ,${ENABLED_SERVICES} =~ ,"monasca-storm" ]] && return 0
    return 1
}

function start_storm {
    if is_storm_enabled; then
        echo_summary "Starting storm-{nimbus,supervisor}"
        run_process "monasca-storm-nimbus" "${STORM_NIMBUS_CMD}" "${STORM_GROUP}" "${STORM_USER}"
        run_process "monasca-storm-supervisor" "${STORM_SUPERVISOR_CMD}" "${STORM_GROUP}" "${STORM_USER}"
    fi
}

function stop_storm {
    if is_storm_enabled; then
        echo_summary "Stopping storm-{nimbus,supervisor}"
        stop_process "monasca-storm-nimbus"
        stop_process "monasca-storm-supervisor"
    fi
}

function clean_storm {
    if is_storm_enabled; then
        echo_summary "Cleaning storm"

        sudo unlink "${DEST}/logs/storm-workers" || true
        sudo unlink "${STORM_CURRENT_DIR}/logs"|| true
        sudo unlink "${STORM_CURRENT_DIR}"|| true

        sudo rm -rf "${DEST}/logs/storm-workers" || true
        sudo rm -rf "${STORM_CURRENT_DIR}"|| true
        sudo rm -rf "${STORM_DIR}" || true
        sudo rm -rf "${STORM_WORK_DIR}" || true
        sudo rm -rf "${STORM_LOG_DIR}" || true

        sudo userdel "${STORM_USER}" || true
        sudo groupdel "${STORM_GROUP}" || true
    fi
}

function configure_storm {
    if is_storm_enabled; then
        echo_summary "Configuring storm"
        sudo cp -f "${MONASCA_API_DIR}"/devstack/files/storm.yaml "${STORM_CURRENT_DIR}/conf/storm.yaml"
        sudo chown "${STORM_USER}":"${STORM_GROUP}" "${STORM_CURRENT_DIR}/conf/storm.yaml"
        sudo chmod 0644 "${STORM_CURRENT_DIR}/conf/storm.yaml"
    fi
}

function install_storm {
    if is_storm_enabled; then
        echo_summary "Installing storm"
        _download_storm
        _setup_user_group
        _install_storm
        _create_directories
    fi
}

# helpers

function _download_storm {
    local storm_tarball_url="${APACHE_MIRROR}storm/apache-storm-${STORM_VERSION}/${STORM_TARBALL}"
    download_file "${storm_tarball_url}" "${STORM_TARBALL_DEST}"
}

function _setup_user_group {
    sudo groupadd --system "${STORM_GROUP}" || true
    sudo useradd --system -g "${STORM_GROUP}" "${STORM_USER}" || true
}

function _install_storm {
    sudo mkdir -p "${STORM_DIR}" || true
    sudo chown "${STORM_USER}":"${STORM_GROUP}" "${STORM_DIR}"

    sudo chmod 0755 "${STORM_DIR}"

    sudo tar -xzf ${STORM_TARBALL_DEST} -C "${STORM_DIR}"
    sudo ln -sf "${STORM_DIR}/apache-storm-${STORM_VERSION}" "${STORM_CURRENT_DIR}"
}

function _create_directories {
    sudo mkdir "${STORM_WORK_DIR}" || true
    sudo chown "${STORM_USER}":"${STORM_GROUP}" "${STORM_WORK_DIR}"
    sudo chmod 0775 "${STORM_WORK_DIR}"

    sudo mkdir "${STORM_LOG_DIR}" || true
    sudo chown "${STORM_USER}":"${STORM_GROUP}" "${STORM_LOG_DIR}"
    sudo chmod 0775 "${STORM_LOG_DIR}"

    # make them visible in stander location
    sudo ln -sf "${STORM_LOG_DIR}" "${STORM_CURRENT_DIR}/logs/"

    # if inside the gate, make the visible there too
    sudo ln -sf "${STORM_LOG_DIR}/workers-artifacts/" "${DEST}/logs/storm-workers/"
}

# helpers

$_XTRACE_STORM
