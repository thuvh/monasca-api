#
# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
# (C) Copyright 2017 FUJITSU LIMITED
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

function load_devstack_utilities {
    source $BASE/new/devstack/stackrc
    source $BASE/new/devstack/functions
    source $BASE/new/devstack/openrc admin admin
}

function setup_monasca {

    local constraints="-c $REQUIREMENTS_DIR/upper-constraints.txt"

    (cd $DEST/tempest/; sudo virtualenv .venv)
    source $DEST/tempest/.venv/bin/activate

    (cd $DEST/tempest/; sudo pip install -r requirements.txt -r test-requirements.txt)
    sudo pip install nose
    sudo pip install numpy

    pushd $MONASCA_API_DIR
    sudo -H pip install $constraints -U -r requirements.txt -r test-requirements.txt
    sudo python setup.py install
    popd
}

function set_tempest_conf {

    (cd $DEST/tempest/; oslo-config-generator --config-file  tempest/cmd/config-generator.tempest.conf  --output-file etc/tempest.conf)

    cp -f $DEST/tempest/etc/logging.conf.sample $DEST/tempest/etc/logging.conf

    # set identity section
    iniset $DEST/tempest/etc/tempest.conf identity admin_domain_scope True
    iniset $DEST/tempest/etc/tempest.conf identity user_unique_last_password_count 2
    iniset $DEST/tempest/etc/tempest.conf identity user_locakout_duration 5
    iniset $DEST/tempest/etc/tempest.conf identity user_lockout_failure_attempts 2
    iniset $DEST/tempest/etc/tempest.conf identity uri $OS_AUTH_URL/v2.0
    iniset $DEST/tempest/etc/tempest.conf identity uri_v3 $OS_AUTH_URL/v3
    iniset $DEST/tempest/etc/tempest.conf identity auth_version v$OS_IDENTITY_API_VERSION
    # set auth section
    iniset $DEST/tempest/etc/tempest.conf auth use_dynamic_credentials True
    iniset $DEST/tempest/etc/tempest.conf auth admin_username $OS_USERNAME
    iniset $DEST/tempest/etc/tempest.conf auth admin_password $OS_PASSWORD
    iniset $DEST/tempest/etc/tempest.conf auth admin_domain_name $OS_PROJECT_DOMAIN_ID
    iniset $DEST/tempest/etc/tempest.conf auth admin_project_name $OS_PROJECT_NAME

}

function run_tempest_test {

    (cd $DEST/tempest/; sudo testr init)

    (cd $DEST/tempest/; sudo sh -c 'testr list-tests monasca_tempest_tests > monasca_tempest_tests')
    (cd $DEST/tempest/; sudo sh -c 'cat monasca_tempest_tests')
    (cd $DEST/tempest/; sudo sh -c 'cat monasca_tempest_tests | grep gate > monasca_tempest_tests_gate')
    (cd $DEST/tempest/; sudo sh -c 'testr run --subunit --load-list=monasca_tempest_tests_gate | subunit-trace --fails')

}

function run_post_hook {
    XTRACE=$(set +o | grep xtrace)
    set -o xtrace

    echo_summary "monasca's post_test_hook.sh was called..."
    (set -o posix; set)

    # save ref to monasca-api dir
    export MONASCA_API_DIR="$BASE/monasca-api"
    #sudo chown -R jenkins:$STACK_USER $MONASCA_API_DIR

    load_devstack_utilities
    setup_monasca

    # Run functional tests
    echo "Running monasca tempest test suite"
    set_tempest_conf
    run_tempest_test
}

function  function_exists {
    declare -f -F $1 > /dev/null
}

if ! function_exists echo_summary; then
    function echo_summary {
        echo $@
    }
fi

run_post_hook