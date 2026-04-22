"""Reconcile missing schema columns and tables

This migration defensively adds schema elements that exist in the SQLAlchemy
models but may be absent from databases that were migrated via the old
migration chain (formhook/app/migrations/versions/), where the shared
revision ID 'add_is_admin_flag' caused Alembic to believe the DB was already
at head without having applied token_version, password_resets, or
auth_security_counters.

Revision ID: 20260422_reconcile_missing_schema
Revises: add_is_admin_flag
Create Date: 2026-04-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '20260422_reconcile_missing_schema'
down_revision: Union[str, Sequence[str], None] = 'add_is_admin_flag'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Widen the alembic_version tracking column so that revision IDs longer
    # than the legacy VARCHAR(32) limit can be recorded without error.
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE TEXT")

    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # --- users.token_version ---
    existing_user_columns = {col["name"] for col in inspector.get_columns('users')}
    if 'token_version' not in existing_user_columns:
        op.add_column(
            'users',
            sa.Column('token_version', sa.Integer(), nullable=False, server_default='0')
        )

    # --- password_resets table ---
    if 'password_resets' not in existing_tables:
        op.create_table(
            'password_resets',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('token', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('is_used', sa.Boolean(), server_default='false', nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_password_resets_id'), 'password_resets', ['id'], unique=False)
        op.create_index(op.f('ix_password_resets_token'), 'password_resets', ['token'], unique=True)

    # --- auth_security_counters table ---
    if 'auth_security_counters' not in existing_tables:
        op.create_table(
            'auth_security_counters',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('endpoint', sa.String(length=64), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('ip_address', sa.String(length=64), nullable=False),
            sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint(
                'endpoint', 'email', 'ip_address',
                name='uq_auth_security_counter_key'
            )
        )
        op.create_index(
            op.f('ix_auth_security_counters_id'), 'auth_security_counters', ['id'], unique=False
        )
        op.create_index(
            op.f('ix_auth_security_counters_endpoint'), 'auth_security_counters', ['endpoint'], unique=False
        )
        op.create_index(
            op.f('ix_auth_security_counters_email'), 'auth_security_counters', ['email'], unique=False
        )
        op.create_index(
            op.f('ix_auth_security_counters_ip_address'), 'auth_security_counters', ['ip_address'], unique=False
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    existing_user_columns = {col["name"] for col in inspector.get_columns('users')}

    if 'auth_security_counters' in existing_tables:
        op.drop_index(op.f('ix_auth_security_counters_ip_address'), table_name='auth_security_counters')
        op.drop_index(op.f('ix_auth_security_counters_email'), table_name='auth_security_counters')
        op.drop_index(op.f('ix_auth_security_counters_endpoint'), table_name='auth_security_counters')
        op.drop_index(op.f('ix_auth_security_counters_id'), table_name='auth_security_counters')
        op.drop_table('auth_security_counters')

    if 'password_resets' in existing_tables:
        op.drop_index(op.f('ix_password_resets_token'), table_name='password_resets')
        op.drop_index(op.f('ix_password_resets_id'), table_name='password_resets')
        op.drop_table('password_resets')

    if 'token_version' in existing_user_columns:
        op.drop_column('users', 'token_version')
