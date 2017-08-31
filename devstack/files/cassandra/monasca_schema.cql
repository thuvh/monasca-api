
// (C) Copyright 2017 SUSE LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
// implied.
// See the License for the specific language governing permissions and
// limitations under the License.


drop schema if exists monasca;

// Need to tune strategy
create schema monasca with replication = { 'class' : 'SimpleStrategy', 'replication_factor' : 1 };

create table monasca.measurements (
    metric_id blob,
    time_stamp timestamp,
    value double,
    value_meta text,
primary key (metric_id, time_stamp)
) 
WITH CLUSTERING ORDER BY (time_stamp DESC);

//need to compare SASI and native index which supports collections
create table monasca.metrics (
    region text,
    tenant_id text,
    metric_name text,
    dimensions frozen<map<text, text>>,
    metric_id blob,
primary key ((region, tenant_id, metric_name), dimensions)
);

create table monasca.dimensions (
    region text,
    tenant_id text,
    name text,
    value text,
    metric_id blob,
primary key ((region, tenant_id, name), value, metric_id)
);

create table monasca.dimensions_metrics (
    region text,
    tenant_id text,
    dimension_name text,
    dimension_value text,
    metric_name text,
    metric_id blob,
primary key ((region, tenant_id, dimension_name, dimension_value), metric_name, metric_id)
);

CREATE MATERIALIZED VIEW monasca.metrics_dimensions
    AS SELECT metric_id
    FROM monasca.dimensions_metrics
    WHERE region IS NOT NULL and tenant_id IS NOT NULL and dimension_name IS NOT NULL AND dimension_value IS NOT NULL and metric_name IS NOT NULL and metric_id IS NOT NULL
    PRIMARY KEY ((region, tenant_id, metric_name), dimension_name, dimension_value, metric_id);

create table monasca.alarm_state_history (
        alarm_id text,
        metric text static,
        time_stamp timestamp,
        tenant_id text,
        old_state text,
        new_state text,
        subalarms text,
        reason text,
        reason_data text,
primary key (tenant_id, alarm_id, time_stamp)
);

