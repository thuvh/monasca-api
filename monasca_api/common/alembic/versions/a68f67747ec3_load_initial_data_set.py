"""load initial data set

Revision ID: a68f67747ec3
Revises: c71d5f791525
Create Date: 2017-06-05 07:38:43.891249

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a68f67747ec3'
down_revision = 'c71d5f791525'
branch_labels = None
depends_on = None

_ALARM_STATE_OK = 'OK'
_ALARM_STATE_UNDETERMINED = 'UNDETERMINED'
_ALARM_STATE_ALARM = 'ALARM'

_ALARM_DEF_SEV_LOW = 'LOW'
_ALARM_DEF_SEV_MEDIUM = 'MEDIUM'
_ALARM_DEF_SEV_HIGH = 'HIGH'
_ALARM_DEF_SEV_CRITICAL = 'CRITICAL'

_NOTIFICATION_METHOD_EMAIL = 'EMAIL'
_NOTIFICATION_METHOD_WEBHOOK = 'WEBHOOK'
_NOTIFICATION_METHOD_PAGERDUTY = 'PAGERDUTY'

_ALARM_STATES = (_ALARM_STATE_OK, _ALARM_STATE_UNDETERMINED,
                 _ALARM_STATE_ALARM)
_ALARM_SEVERITIES = (_ALARM_DEF_SEV_LOW, _ALARM_DEF_SEV_MEDIUM,
                     _ALARM_DEF_SEV_HIGH, _ALARM_DEF_SEV_CRITICAL)
_NOTIFICATION_METHODS = (_NOTIFICATION_METHOD_EMAIL,
                         _NOTIFICATION_METHOD_PAGERDUTY,
                         _NOTIFICATION_METHOD_WEBHOOK)


def upgrade():
    alarm_state = sa.Table('alarm_state',
                           autoload=True)
    alarm_definition_severity = sa.Table('alarm_definition_severity',
                                         autoload=True)
    notification_method_type = sa.Table('notification_method_type',
                                        autoload=True)

    # bind tables to data
    binding = (
        (alarm_state, _ALARM_STATES),
        (alarm_definition_severity, _ALARM_SEVERITIES),
        (notification_method_type, _NOTIFICATION_METHODS)
    )

    for table, data in binding:
        data = [{'name': value for value in data}]
        op.bulk_insert(table, data)


def downgrade():
    tables = ['alarm_state', 'alarm_definition_severity',
              'notification_method_type']
    for table in tables:
        op.execute('delete from %s' % table)
