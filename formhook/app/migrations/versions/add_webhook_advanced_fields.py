"""
Add webhook_headers and webhook_secret to forms table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('forms', sa.Column('webhook_headers', postgresql.JSONB, nullable=True))
    op.add_column('forms', sa.Column('webhook_secret', sa.String(), nullable=True))

def downgrade():
    op.drop_column('forms', 'webhook_headers')
    op.drop_column('forms', 'webhook_secret')
