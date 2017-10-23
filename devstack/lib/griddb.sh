#!/bin/bash

# Copyright 2017 NEC Corporation
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

_XTRACE_MON_CLIENT=$(set +o | grep xtrace)
set +o xtrace

function install_monasca_griddb {
    echo_summary "Install GridDB Database"

    PACKAGE_NAME="monasca-api"

    apt_get -y install gcc automake autoconf zlib1g-dev ant python

    OLDPATH=$PATH
    export PATH=/usr/lib/jvm/java-9-openjdk-amd64/bin:$OLDPATH

    GRIDDB_SERVER_BUILD_DIR=$(mktemp -dt "$PACKAGE_NAME-devstack_griddb-XXXXXXX")
    trap "popd; sudo rm -rf $GRIDDB_C_CLIENT_BUILD_DIR" EXIT
    pushd $GRIDDB_SERVER_BUILD_DIR

    git clone https://github.com/griddb/griddb_nosql.git
    cd griddb_nosql
    ./bootstrap.sh
    ./configure
    make

    GRIDDB_SERVER_HOME_DIR=/opt/griddb
    getent group griddb || sudo addgroup --system griddb
    getent passwd griddb || sudo adduser --system --ingroup griddb --home $GRIDDB_SERVER_HOME_DIR griddb
    sudo -u griddb cp -rp bin conf log $GRIDDB_SERVER_HOME_DIR
    sudo install -o griddb -g griddb -d $GRIDDB_SERVER_HOME_DIR/data

    export GS_HOME=$GRIDDB_SERVER_HOME_DIR
    export GS_LOG=$GRIDDB_SERVER_HOME_DIR/log
    GS_BIN=$GRIDDB_SERVER_HOME_DIR/bin
    GRIDDB_PASSWORD=${GRIDDB_PASSWORD:-nomoresecure}
    GRIDDB_CLUSTER_NAME=${GRIDDB_CLUSTER_NAME:-monasca}

    sudo -E -u griddb $GS_BIN/gs_passwd admin -p $GRIDDB_PASSWORD
    sudo -u griddb sed -i -e "s/\"clusterName\":.*/\"clusterName\":\"$GRIDDB_CLUSTER_NAME\",/" $GS_HOME/conf/gs_cluster.json
    export no_proxy=127.0.0.1
    sudo -E -u griddb $GS_BIN/gs_startnode
    sudo -E -u griddb $GS_BIN/gs_joincluster -c $GRIDDB_CLUSTER_NAME -u admin/$GRIDDB_PASSWORD

    PATH=$OLDPATH

    echo_summary "Install GridDB C Client"

    ${MONASCA_API_DIR}/tools/install_griddb_c_client.sh devstack
    pip_install_gr -e git+https://github.com/yosshy/griddb_client.git#egg=griddb_python_cilent
}

function clean_monasca_griddb {
    sudo rm -rf /opt/griddb
}

${_XTRACE_MON_CLIENT}
