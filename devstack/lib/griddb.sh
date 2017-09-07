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

function install_monasca_griddb_c_client {
    echo_summary "Install GridDB C Client library"

    apt_get -y install swig

    GRIDDB_C_CLIENT_BUILD_DIR=`mktemp -d -p /tmp/`
    pushd $GRIDDB_C_CLIENT_BUILD_DIR
    git clone https://github.com/griddb/c_client.git
    cd c_client/client/c
    ./bootstrap.sh
    ./configure
    make
    sudo make install
    cd ../../bin
    sudo install -o root -g root -m 0644 libgridstore.so /usr/local/lib
    sudo ldconfig
    popd
    sudo rm -rf $GRIDDB_C_CLIENT_BUILD_DIR

    pip_install_gr -e git+https://github.com/yosshy/griddb_client.git#egg=griddb_python_cilent
}

function clean_monasca_griddb_c_client {
    pip uninstall griddb_python_client
    sudo rm -f /usr/local/lib/libgridstore.so*
    apt_get -y remove swig
}

function install_monasca_griddb {
    install_monasca_griddb_c_client
}

function clean_monasca_griddb {
    clean_monasca_griddb_c_client
}

${_XTRACE_MON_CLIENT}
