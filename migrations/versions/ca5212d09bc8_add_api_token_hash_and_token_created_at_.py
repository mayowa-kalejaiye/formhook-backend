"""add api_token_hash and token_created_at to users

Revision ID: ca5212d09bc8
Revises: caeeba6612ba
Create Date: 2025-07-27 16:57:28.989301

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca5212d09bc8'
down_revision: Union[str, Sequence[str], None] = 'caeeba6612ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    from sqlalchemy import Column, String, DateTime
    op.add_column('users', sa.Column('api_token_hash', sa.String(), nullable=True))
    op.add_column('users', sa.Column('token_created_at', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    op.drop_column('users', 'api_token_hash')
    op.drop_column('users', 'token_created_at')
