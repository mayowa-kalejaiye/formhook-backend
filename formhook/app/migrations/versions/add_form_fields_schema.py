"""
Add fields, redirect_url, and success_message to forms table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('forms', sa.Column('redirect_url', sa.String(), nullable=True))
    op.add_column('forms', sa.Column('success_message', sa.String(), nullable=True))
    op.add_column('forms', sa.Column('fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

def downgrade():
    op.drop_column('forms', 'fields')
    op.drop_column('forms', 'success_message')
    op.drop_column('forms', 'redirect_url')
