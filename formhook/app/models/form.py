"""
Form model definition.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
import uuid
from ..core.database import Base

class Form(Base):
    __tablename__ = "forms"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    webhook_url = Column(String)
    webhook_headers = Column(postgresql.JSONB)
    webhook_secret = Column(String)
    notification_email = Column(String)
    redirect_url = Column(String)
    success_message = Column(String)
    fields = Column(postgresql.JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    api_token = Column(String, nullable=True, unique=True, index=True, doc="Hashed API token for form submissions.")
    require_token = Column(Integer, default=0, nullable=False, doc="Require API token for submissions (0=False, 1=True)")
    track_location = Column(Integer, default=0, nullable=False, doc="Track geolocation for submissions (0=False, 1=True)")
