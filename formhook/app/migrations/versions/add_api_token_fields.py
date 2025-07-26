"""
Add api_token_hash and token_created_at to users table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('users', sa.Column('api_token_hash', sa.String(), nullable=True))
    op.add_column('users', sa.Column('token_created_at', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    op.drop_column('users', 'api_token_hash')
    op.drop_column('users', 'token_created_at')
