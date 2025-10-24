"""create_push_subscriptions_table

Revision ID: 5fadffbd2fe8
Revises: c116c2a43b4f
Create Date: 2025-10-24 14:37:18.077375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5fadffbd2fe8'
down_revision: Union[str, Sequence[str], None] = 'c116c2a43b4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create push_subscriptions table
    op.create_table(
        'push_subscriptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('p256dh', sa.Text(), nullable=False),
        sa.Column('auth', sa.Text(), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_used', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('endpoint', name='uq_push_subscriptions_endpoint')
    )
    
    # Create indexes for performance
    op.create_index('ix_push_subscriptions_id', 'push_subscriptions', ['id'], unique=False)
    op.create_index('ix_push_subscriptions_user_id', 'push_subscriptions', ['user_id'], unique=False)
    op.create_index('ix_push_subscriptions_endpoint', 'push_subscriptions', ['endpoint'], unique=False)
    op.create_index('ix_push_subscriptions_last_used', 'push_subscriptions', ['last_used'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_push_subscriptions_last_used', table_name='push_subscriptions')
    op.drop_index('ix_push_subscriptions_endpoint', table_name='push_subscriptions')
    op.drop_index('ix_push_subscriptions_user_id', table_name='push_subscriptions')
    op.drop_index('ix_push_subscriptions_id', table_name='push_subscriptions')
    
    # Drop table
    op.drop_table('push_subscriptions')
