"""add device metadata columns to submissions

Revision ID: 20251208_add_submission_device_metadata
Revises: add_trial_metadata
Create Date: 2025-12-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '20251208_add_submission_device_metadata'
down_revision: Union[str, Sequence[str], None] = 'add_trial_metadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = 'submissions'


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {col["name"] for col in inspector.get_columns(TABLE_NAME)}

    if 'device_type' not in existing:
        op.add_column(TABLE_NAME, sa.Column('device_type', sa.String(length=32), nullable=True))
    if 'user_agent' not in existing:
        op.add_column(TABLE_NAME, sa.Column('user_agent', sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {col["name"] for col in inspector.get_columns(TABLE_NAME)}

    if 'device_type' in existing:
        op.drop_column(TABLE_NAME, 'device_type')
    if 'user_agent' in existing:
        op.drop_column(TABLE_NAME, 'user_agent')
