"""
Alembic migration to add api_token and require_token fields to forms table.

Revision ID: add_api_token_and_require_token
Revises: 0355395e236c
Create Date: 2025-07-27 18:10:00.000000
"""
revision = 'add_api_token_and_require_token'
down_revision = '0355395e236c'
branch_labels = None
depends_on = None
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('forms', sa.Column('api_token', sa.String(), nullable=True, unique=True))
    op.add_column('forms', sa.Column('require_token', sa.Integer(), nullable=False, server_default='0'))

def downgrade():
    op.drop_column('forms', 'api_token')
    op.drop_column('forms', 'require_token')
