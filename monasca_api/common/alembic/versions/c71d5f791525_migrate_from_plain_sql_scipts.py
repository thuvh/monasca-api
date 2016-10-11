"""sql from plain sql scipts

Revision ID: c71d5f791525
Revises:
Create Date: 2017-06-05 07:38:32.909500

"""
from alembic import op
from oslo_log import log
import sqlalchemy as sa

LOG = log.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = 'c71d5f791525'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    alarm_state = op.create_table(
            'alarm_state',
            sa.Column('name', sa.String(length=20),
                      primary_key=True, nullable=False,
                      unique=True))

    alarm_definition_severity = op.create_table(
            'alarm_definition_severity',
            sa.Column('name', sa.String(length=20),
                      primary_key=True, nullable=False,
                      unique=True))

    notification_method_type = op.create_table(
            'notification_method_type',
            sa.Column('name', sa.String(length=20),
                      primary_key=True, nullable=False,
                      unique=True))

    notification_method = op.create_table(
            'notification_method',
            sa.Column('id', sa.String(length=36),
                      primary_key=True, nullable=False),
            sa.Column('tenant_id', sa.String(36), nullable=False),
            sa.Column('name', sa.String(250), default=None),
            sa.Column('type', sa.String(20),
                      sa.ForeignKey(notification_method_type.c.name),
                      nullable=False),
            sa.Column('address', sa.String(512), nullable=False),
            sa.Column('period', sa.Integer, nullable=False, default=0),
            sa.Column('created_at', sa.DateTime, nullable=False),
            sa.Column('updated_at', sa.DateTime, nullable=False))

    alarm_definition = op.create_table(
            'alarm_definition',
            sa.Column('id', sa.String(length=36),
                      primary_key=True, nullable=False),
            sa.Column('tenant_id', sa.String(36),
                      index=True, nullable=False),
            sa.Column('name', sa.String(255), nullable=False, default=''),
            sa.Column('description', sa.String(255), default=None,
                      nullable=True),
            sa.Column('expression', sa.Text(), nullable=False),
            sa.Column('severity', sa.String(20),
                      sa.ForeignKey(alarm_definition_severity.c.name),
                      nullable=False),
            sa.Column('match_by', sa.String(255), default=''),
            sa.Column('actions_enabled', sa.Boolean(), default=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), index=True,
                      nullable=False))

    alarm = op.create_table(
            'alarm',
            sa.Column('id', sa.String(length=36),
                      primary_key=True, nullable=False),
            sa.Column('alarm_definition_id', sa.String(length=36),
                      sa.ForeignKey(alarm_definition.c.id,
                                    name='fk_alarm_definition_id',
                                    ondelete='cascade'),
                      index=True, nullable=False),
            sa.Column('state', sa.String(20),
                      sa.ForeignKey(alarm_state.c.name,
                                    name='fk_alarm_alarm_state'),
                      nullable=False),
            sa.Column('lifecycle_state', sa.String(50),
                      nullable=True, default=None),
            sa.Column('link', sa.String(512), nullable=True, default=None),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('state_updated_at', sa.DateTime())
    )

    op.create_table(
            'alarm_action',
            sa.Column('alarm_definition_id', sa.String(length=36),
                      sa.ForeignKey(alarm_definition.c.id,
                                    ondelete='cascade'),
                      nullable=False),
            sa.Column('alarm_state', sa.String(20),
                      sa.ForeignKey(alarm_state.c.name),
                      nullable=False),
            sa.Column('action_id', sa.String(36),
                      sa.ForeignKey(notification_method.c.id,
                                    ondelete='cascade'),
                      nullable=False),
            sa.PrimaryKeyConstraint('alarm_alarm_definition_id',
                                    'alarm_state',
                                    'action_id'))

    op.create_table(
            'alarm_metric',
            sa.Column('alarm_id', sa.String(36),
                      sa.ForeignKey(alarm.c.id, ondelete='cascade'),
                      index=True, nullable=False),
            sa.Column('metric_definition_dimensions_id', sa.Binary(),
                      index=True, nullable=False))

    op.create_table(
            'metric_definition',
            sa.Column('id', sa.Binary(), primary_key=True, nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('tenant_id', sa.String(255), nullable=False),
            sa.Column('region', sa.String(255), nullable=False))

    op.create_table(
            'metric_definition_dimensions',
            sa.Column('id', sa.Binary(), nullable=False),
            sa.Column('metric_definition_id', sa.Binary(),
                      index=True, nullable=False),
            sa.Column('metric_dimension_set_id', sa.Binary(),
                      index=True, nullable=False))

    op.create_table(
            'metric_dimension',
            sa.Column('dimension_set_id', sa.Binary(),
                      index=True, nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('value', sa.String(255), nullable=False),
            sa.UniqueConstraint('name', 'dimension_set_id',
                                name='metric_dimension_key'))

    sub_alarm_definition = op.create_table(
            'sub_alarm_definition',
            sa.Column('id', sa.String(length=36),
                      primary_key=True, nullable=False),
            sa.Column('alarm_definition_id', sa.String(36), nullable=False),
            sa.Column('function', sa.String(10), nullable=False),
            sa.Column('metric_name', sa.String(100), nullable=False),
            sa.Column('operator', sa.String(5), nullable=False),
            sa.Column('threshold', sa.Float, nullable=False),
            sa.Column('period', sa.Integer(), nullable=False),
            sa.Column('periods', sa.Integer(), nullable=False),
            sa.Column('is_deterministic', sa.Boolean,
                      nullable=False, default=False),
            sa.Column('created_at', sa.DateTime),
            sa.Column('updated_at', sa.DateTime))

    op.create_table(
            'sub_alarm_definition_dimension',
            sa.Column('sub_alarm_definition_id', sa.String(36),
                      sa.ForeignKey(sub_alarm_definition.c.id,
                                    ondelete='cascade'),
                      nullable=False),
            sa.Column('dimension_name', sa.String(255), default=None),
            sa.Column('value', sa.String(255), default=None))

    op.create_table(
            'sub_alarm',
            sa.Column('id', sa.String(length=36),
                      primary_key=True, nullable=False),
            sa.Column('alarm_id', sa.String(36),
                      sa.ForeignKey(alarm.c.id, ondelete='cascade'),
                      sa.ForeignKey(sub_alarm_definition.c.id),
                      nullable=False, default=''),
            sa.Column('sub_expression_id', sa.String(36),
                      nullable=False, default=''),
            sa.Column('expression', sa.Text(), nullable=False),
            sa.Column('state', sa.String(20),
                      sa.ForeignKey(alarm_state.c.name),
                      nullable=False, default='OK'),
            sa.Column('created_at', sa.DateTime),
            sa.Column('updated_at', sa.DateTime))


def downgrade():
    op.drop_table('sub_alarm')
    op.drop_table('sub_alarm_definition_dimension')
    op.drop_table('sub_alarm_definition')
    op.drop_table('notification_method')
    op.drop_table('metric_dimension')
    op.drop_table('metric_definition_dimensions')
    op.drop_table('metric_definition')
    op.drop_table('alarm_metric')
    op.drop_table('alarm_definition')
    op.drop_table('alarm_action')
    op.drop_table('alarm')
    op.drop_table('alarm_definition_severity')
    op.drop_table('notification_method_type')
    op.drop_table('alarm_state')
