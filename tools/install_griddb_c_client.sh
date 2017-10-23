#!/usr/bin/env bash

PACKAGE_NAME=monasca-api

mode=$1
case $mode in
tox|devstack)
	;;
*)
	echo "usage: $0 <tox|devstack>"
	exit 1
	;;
esac

set -e

ldconfig -p | grep -q libgridstore.so && exit 0
if [ -n "$LD_LIBRARY_PATH" ]; then
   IFS=":"
   for path in $LD_LIBRARY_PATH; do
      test -f ${path}/libgridstore.so && exit 0
   done
fi

GRIDDB_C_CLIENT_BUILD_DIR=$(mktemp -dt "$PACKAGE_NAME-install_griddb_c_client-XXXXXXX")
trap "popd; rm -rf $GRIDDB_C_CLIENT_BUILD_DIR" EXIT
pushd $GRIDDB_C_CLIENT_BUILD_DIR

git clone https://github.com/griddb/c_client.git
cd c_client/client/c
./bootstrap.sh

case $mode in
tox)
	./configure --libdir=${VIRTUAL_ENV}/lib
	make
	make install
	;;
devstack)
	./configure
	make
	sudo make install
	;;
esac

exit 0
