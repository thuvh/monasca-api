1. Clone the OpenStack tempest repo, and cd to it.
2. Create a virtualenv for running the Tempest tests and activate it. For example in the tempest root dir
    
    ```
        virtualenv .venv
        .venv/bin/activate
    ``` 
3. Install Tempest requirements.

    ```
        pip install -r requirements.txt -t test-requirements.txt
        pip install nose
    ```
4. Create ```etc/tempest.conf``` and ```etc/logging.conf``` in the tempest root dir.
5. Clone the monasca-api repo, cd to it, fetch this review, and create a branch.
5. Install the monasca-api in your venv, which will also register
the Monasca Tempest Plugin as, monasca_tempest_tests. See http://docs.openstack.org/developer/tempest/plugin.html, for more details on Tempest Plugins and the registration process.

    ````    
        python setup.py install
    ````
7. Run the tests using testr.
    
    7.1 In the Tempest root dir, create a list of the Monasca Tempest Tests
in a file.

    ````
    testr list-tests monasca_tempest_tests > monasca_tempest_tests
    ````
    7.2 Run the tests using testr
    
    ````
    testr run --load-list=monasca_tempest_tests
    ````
7. Alternatively, to run the tests using ostestr (no file necessary)

    ````
       ostestr --regex monasca_tempest_tests
    ````