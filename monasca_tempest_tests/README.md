# Configuring to run the Monasca Tempest Tests
1. Clone the OpenStack Tempest repo, and cd to it.
2. Create a virtualenv for running the Tempest tests and activate it. For example in the Tempest root dir
    
    ```
        virtualenv .venv
        .venv/bin/activate
    ``` 
3. Install Tempest requirements in the virtualenv.

    ```
        pip install -r requirements.txt -t test-requirements.txt
        pip install nose
    ```
4. Create ```etc/tempest.conf``` and ```etc/logging.conf``` in the Tempest root dir. Add the following sections to ```tempest.conf```

    ```
    [identity]

    username = mini-mon
    password = password
    tenant_name = mini-mon
    domain_name = default
    admin_username = admin
    admin_password = admin
    admin_domain_name = default
    admin_tenant_name = admin
    alt_username = mini-mon
    alt_password = password
    alt_tenant_name = mini-mon
    use_ssl = False
    auth_version = v3
    uri = http://192.168.10.5:5000/v2.0/
    uri_v3 = http://192.168.10.5:35357/v3/

    [auth]

    allow_tenant_isolation = true
    tempest_roles = monasca-user
    ```
5. Clone the monasca-api repo, cd to it, fetch this review, and create a branch.
6. Install the monasca-api in your venv, which will also register
the Monasca Tempest Plugin as, monasca_tempest_tests.

    ````    
        python setup.py install
    ````
See http://docs.openstack.org/developer/tempest/plugin.html, for more details on Tempest Plugins and the registration process.

# Running the Monasca Tests
## Run the tests from the CLI using testr
    
1. In the Tempest root dir, create a list of the Monasca Tempest Tests in a file.

    ````
    testr list-tests monasca_tempest_tests > monasca_tempest_tests
    ````
2. Run the tests using testr
    
    ````
    testr run --load-list=monasca_tempest_tests
    ````

## Run the tests from the CLI using ostestr (no file necessary)
In the Tempest root dir

    ````
       ostestr --regex monasca_tempest_tests
    ````

## Running/Debugging the Monasca Tempest Tests in PyCharm
1. In PyCharm, Edit Configurations and add a new Python tests configuration by selecting Python tests->Nosetests.
2. Name the test. For example TestVersions.
3. Set the path to the script with the tests to run. For example, ~/repos/monasca-api/monasca_tempest_tests/api/test_versions.py
4. Set the name of the Class to test. For example TestVersions.
5. Set the working directory to your local root Tempest repo. For example, ~/repos/tempest.
6. Select the Python interpreter for you project to be the same as the on virtualenv created above. For example, ~/repos/tempest/.venv
7. Run the tests. You should also be able to debug them.
8. Step and repeat for other tests.