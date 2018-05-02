..
    monasca-api documentation master file
    Copyright 2017 FUJITSU LIMITED

    Licensed under the Apache License, Version 2.0 (the "License"); you may
    not use this file except in compliance with the License. You may obtain
    a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
    License for the specific language governing permissions and limitations
    under the License.

===================================
Welcome to Monasca's Documentation!
===================================

The monitoring requirements in OpenStack environments are vast, varied, and
highly complex. Monasca's project mission is to provide a
monitoring-as-a-service solution that is multi-tenant, highly scalable,
performant, and fault-tolerant. Monasca provides an extensible platform for
advanced monitoring that can be used by both operators and tenants to gain
operational insights about their infrastructure and applications.

Monasca uses REST APIs for high-speed metrics, logs processing and querying. It
integrates a streaming alarm engine, a notification engine and an aggregation
engine.

The use cases you can implement with Monasca are very diverse. Monasca follows
a micro-services architecture, with several services split across multiple
repositories. Each module is designed to provide a discrete service in the
overall monitoring solution and can be deployed or omitted according to
operators/customers needs.

Architecture
============

.. image:: /_static/images/architecture.png
  :width: 900 px

Repositories
------------

* `monasca-api <https://github.com/openstack/monasca-api>`_:
  RESTful API for metrics, alarms and notifications.
* `monasca-agent <https://github.com/openstack/monasca-agent>`_:
  Agent for retrieving metrics data.
* `monasca-persister <https://github.com/openstack/monasca-persister>`_:
  Writes metrics to a time-series database.
* `monasca-thresh <https://github.com/openstack/monasca-thresh>`_:
  Thresholding engine, processes metrics and determines alarm states.
* `monasca-notification <https://github.com/openstack/monasca-notification>`_:
  Delivers notifications when an alarm state transitions.
* `monasca-transform <https://github.com/openstack/monasca-transform>`_:
  Aggregation engine based on Apache Spark.
* `monasca-aggregator <https://github.com/monasca/monasca-aggregator>`_:
  Light-weight metrics aggregator.

Apart from sending requests directly to the API, following tools are available
for interacting with Monasca:

* `Monasca Client <https://github.com/openstack/python-monascaclient>`_:
  CLI and Python client.
* `Horizon plugin <https://github.com/openstack/monasca-ui>`_:
  Implements monitoring panel for Horizon.
* `Grafana app <https://github.com/monasca/monasca-grafana>`_:
  Plugin for Grafana.

Libraries:

* `monasca-common <https://github.com/openstack/monasca-common>`_:
  common code used in Monasca components.
* `monasca-statsd <https://github.com/openstack/monasca-statsd>`_:
  statsd-compatible library for sending metrics from instrumented applications
  to Monasca.

Grafana__ integration:

* `monasca-grafana-datasource
  <https://github.com/openstack/monasca-grafana-datasource>`_:
  multi-tenant Monasca data source for Grafana
* `grafana <https://github.com/monasca/grafana>`_:
  Forked version of Grafana 4.1.2 with added Keystone authentication

__ https://grafana.com/

For Contributors
================

.. toctree::
   :maxdepth: 1

   contributor/index

For Operators
================

Configuration
-------------

* :doc:`Sample Config Files </configuration/sample>`

.. toctree::
   :hidden:

   admin/index
   cli/index
   configuration/sample
   glossary
   install/index
   user/index
