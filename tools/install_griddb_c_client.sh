#!/usr/bin/env bash

PACKAGE_NAME=monasca-api

set -e

ldconfig -p | grep -q libgridstore.so && exit 0

GRIDDB_C_CLIENT_BUILD_DIR=$(mktemp -dt "$PACKAGE_NAME-install_griddb_c_client-XXXXXXX")
trap "popd; sudo rm -rf $GRIDDB_C_CLIENT_BUILD_DIR" EXIT
pushd $GRIDDB_C_CLIENT_BUILD_DIR

sudo apt-get install -y swig libtool m4

git clone https://github.com/griddb/c_client.git
cd c_client/client/c
./bootstrap.sh
./configure
make
sudo make install
cd ../../bin
sudo install -o root -g root -m 0644 libgridstore.so /usr/local/lib
sudo ldconfig

exit 0
