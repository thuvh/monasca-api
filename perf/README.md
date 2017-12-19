
monasca-api performance benchmarking
=============

Recommended Configuration
=============

Install
=======

Install JMeter
add JMeter bin to the path: PATH=$PATH:~/.../bin

Monasca-query performance test
==============================

This test is designed to work with data created from persister-perf performance test but
can work with any monasca-api/db configuration.
monasca-api will need to have region configured to support test data.
JMeter uses monasca-api to query db backend.

Load monasca_queryr_test.jmx into jmeter.
Setup user defined variables for your environment.
Run tests.
