"""Add subscription and usage tracking fields to users

Revision ID: add_subscription_tracking
Revises: 
Create Date: 2025-09-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_subscription_tracking'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add subscription and usage tracking fields to users table."""
    # Add subscription tracking columns
    op.add_column('users', sa.Column('subscription_tier', sa.String(), nullable=False, server_default='free'))
    op.add_column('users', sa.Column('subscription_status', sa.String(), nullable=False, server_default='active'))
    op.add_column('users', sa.Column('subscription_start_date', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('users', sa.Column('subscription_end_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('billing_cycle', sa.String(), nullable=False, server_default='monthly'))
    
    # Add usage tracking columns
    op.add_column('users', sa.Column('current_period_start', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('users', sa.Column('current_period_submissions', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('total_submissions', sa.Integer(), nullable=False, server_default='0'))
    
    # Add payment integration columns
    op.add_column('users', sa.Column('stripe_customer_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('stripe_subscription_id', sa.String(), nullable=True))
    
    # Add metadata columns
    op.add_column('users', sa.Column('usage_metadata', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('subscription_metadata', sa.JSON(), nullable=True))
    
    # Create indexes for better query performance
    op.create_index('ix_users_subscription_tier', 'users', ['subscription_tier'])
    op.create_index('ix_users_subscription_status', 'users', ['subscription_status'])
    op.create_index('ix_users_current_period_start', 'users', ['current_period_start'])
    op.create_index('ix_users_stripe_customer_id', 'users', ['stripe_customer_id'])


def downgrade() -> None:
    """Remove subscription and usage tracking fields from users table."""
    # Drop indexes
    op.drop_index('ix_users_stripe_customer_id', table_name='users')
    op.drop_index('ix_users_current_period_start', table_name='users')
    op.drop_index('ix_users_subscription_status', table_name='users')
    op.drop_index('ix_users_subscription_tier', table_name='users')
    
    # Drop columns
    op.drop_column('users', 'subscription_metadata')
    op.drop_column('users', 'usage_metadata')
    op.drop_column('users', 'stripe_subscription_id')
    op.drop_column('users', 'stripe_customer_id')
    op.drop_column('users', 'total_submissions')
    op.drop_column('users', 'current_period_submissions')
    op.drop_column('users', 'current_period_start')
    op.drop_column('users', 'billing_cycle')
    op.drop_column('users', 'subscription_end_date')
    op.drop_column('users', 'subscription_start_date')
    op.drop_column('users', 'subscription_status')
    op.drop_column('users', 'subscription_tier')
