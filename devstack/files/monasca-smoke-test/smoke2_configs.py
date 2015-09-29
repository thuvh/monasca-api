# -*- encoding: utf-8 -*-

"""configurations for smoke2 test"""

test_config = {
    'default': {   # the default configuration,
                   # simple test of each component of monasca-vagrant
        'kafka': {
            'topics': [
                'metrics', 'events', 'raw-events', 'transformed-events',
                'stream-definitions', 'transform-definitions',
                'alarm-state-transitions', 'alarm-notifications',
                'retry-notifications'
            ]
        },
        'mysql_schema': [
            'alarm', 'alarm_action', 'alarm_definition', 'alarm_metric',
            'metric_definition', 'metric_definition_dimensions',
            'metric_dimension', 'notification_method', 'schema_migrations',
            'stream_actions', 'stream_definition', 'sub_alarm',
            'sub_alarm_definition', 'sub_alarm_definition_dimension',
            'event_transform', 'alarm_state', 'alarm_definition_severity',
            'notification_method_type', 'stream_actions_action_type'
        ],
        'arg_defaults': {
            'dbtype': "influxdb",
            'kafka': "127.0.0.1:9092",
            'zoo': "127.0.0.1:2181",
            'mysql': "127.0.0.1",
            'monapi': "127.0.0.1",

        },

        'check': {
            'expected_processes': [
                'apache-storm', 'monasca-api', 'monasca-statsd',
                'monasca-collector', 'monasca-forwarder',
                'monasca-notification', 'monasca-persister',
            ]
        },
    },
    'keystone': {
        'user': "mini-mon",
        'pass': "password",
        'host': "127.0.0.1"
    },
    'storm': "127.0.0.1",
    'mysql': {
        'user': "monapi",
        'pass': "password"
    },
    'influx': {
        'user': "mon_api",
        'pass': "password",
        'node': "http://127.0.0.1:8086"
    },
    'help': {
        'test': 'wiki link for help with specific process'
    }
}
