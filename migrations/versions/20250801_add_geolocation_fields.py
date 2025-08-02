"""
Add geolocation and threat fields to submissions, and track_location to forms
"""
revision = '20250801_add_geolocation_fields'
down_revision = 'add_api_token_and_require_token'
branch_labels = None
depends_on = None
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('submissions', sa.Column('country', sa.String(), nullable=True))
    op.add_column('submissions', sa.Column('region', sa.String(), nullable=True))
    op.add_column('submissions', sa.Column('city', sa.String(), nullable=True))
    op.add_column('submissions', sa.Column('location_source', sa.String(), nullable=True))
    op.add_column('submissions', sa.Column('threat_score', sa.Integer(), nullable=True))
    op.add_column('submissions', sa.Column('latitude', sa.String(), nullable=True))
    op.add_column('submissions', sa.Column('longitude', sa.String(), nullable=True))
    op.add_column('forms', sa.Column('track_location', sa.Integer(), nullable=False, server_default='0'))

def downgrade():
    op.drop_column('submissions', 'country')
    op.drop_column('submissions', 'region')
    op.drop_column('submissions', 'city')
    op.drop_column('submissions', 'location_source')
    op.drop_column('submissions', 'threat_score')
    op.drop_column('submissions', 'latitude')
    op.drop_column('submissions', 'longitude')
    op.drop_column('forms', 'track_location')
