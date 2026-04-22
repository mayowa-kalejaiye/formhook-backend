"""Add is_admin flag to users

Revision ID: add_is_admin_flag
Revises: 20260422_add_auth_security_counters
Create Date: 2025-12-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'add_is_admin_flag'
down_revision: Union[str, Sequence[str], None] = '20260422_add_auth_security_counters'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns('users')}
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('users')}

    if 'is_admin' not in existing_columns:
        op.add_column(
            'users',
            sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        op.alter_column('users', 'is_admin', server_default=None)

    if 'ix_users_is_admin' not in existing_indexes:
        op.create_index('ix_users_is_admin', 'users', ['is_admin'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('users')}
    existing_columns = {col["name"] for col in inspector.get_columns('users')}

    if 'ix_users_is_admin' in existing_indexes:
        op.drop_index('ix_users_is_admin', table_name='users')
    if 'is_admin' in existing_columns:
        op.drop_column('users', 'is_admin')
