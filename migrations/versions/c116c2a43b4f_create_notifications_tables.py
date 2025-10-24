"""create_notifications_tables

Revision ID: c116c2a43b4f
Revises: 4c398d041a24
Create Date: 2025-10-24 14:15:51.441230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c116c2a43b4f'
down_revision: Union[str, Sequence[str], None] = '4c398d041a24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create notifications and notification_preferences tables."""
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('priority', sa.String(10), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notification_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create indexes for notifications
    op.create_index('ix_notifications_id', 'notifications', ['id'], unique=True)
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_type', 'notifications', ['user_id', 'type'])
    op.create_index('ix_notifications_read', 'notifications', ['user_id', 'read'])
    op.create_index('ix_notifications_archived', 'notifications', ['user_id', 'archived'])
    op.create_index('ix_notifications_timestamp', 'notifications', ['user_id', 'timestamp'], postgresql_using='btree', postgresql_ops={'timestamp': 'DESC'})
    
    # Add check constraints for notifications
    op.create_check_constraint(
        'check_notification_type',
        'notifications',
        "type IN ('submission', 'webhook', 'system', 'email', 'security', 'milestone')"
    )
    op.create_check_constraint(
        'check_notification_priority',
        'notifications',
        "priority IN ('low', 'medium', 'high', 'urgent')"
    )
    
    # Create notification_preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('email_notifications', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('webhook_failures', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('security_alerts', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('milestone_alerts', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('submission_alerts', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop notifications and notification_preferences tables."""
    # Drop notification_preferences table
    op.drop_table('notification_preferences')
    
    # Drop check constraints
    op.drop_constraint('check_notification_priority', 'notifications', type_='check')
    op.drop_constraint('check_notification_type', 'notifications', type_='check')
    
    # Drop indexes
    op.drop_index('ix_notifications_timestamp', table_name='notifications')
    op.drop_index('ix_notifications_archived', table_name='notifications')
    op.drop_index('ix_notifications_read', table_name='notifications')
    op.drop_index('ix_notifications_type', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_index('ix_notifications_id', table_name='notifications')
    
    # Drop notifications table
    op.drop_table('notifications')

