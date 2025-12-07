"""Add trial metadata and migrate users to starter tier

Revision ID: add_trial_metadata
Revises: add_subscription_tracking
Create Date: 2025-12-02 00:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timedelta, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = 'add_trial_metadata'
down_revision: Union[str, Sequence[str], None] = '20251129_add_idempotency_keys'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns('users')}

    if 'trial_ends_at' not in existing_columns:
        op.add_column('users', sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True))

    users_table = table(
        'users',
        column('subscription_tier', sa.String()),
        column('subscription_status', sa.String()),
        column('trial_ends_at', sa.DateTime(timezone=True)),
    )

    trial_end = datetime.now(timezone.utc) + timedelta(days=3)

    bind.execute(
        users_table.update()
        .where(users_table.c.subscription_tier == 'free')
        .values(
            subscription_tier='starter',
            subscription_status='trialing',
            trial_ends_at=trial_end,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns('users')}

    if 'trial_ends_at' in existing_columns:
        op.drop_column('users', 'trial_ends_at')
