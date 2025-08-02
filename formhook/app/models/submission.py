"""
Submission model definition.
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from ..core.database import Base

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(String, ForeignKey("forms.id"), nullable=False)
    data = Column(JSONB, nullable=False)
    ip_address = Column(String)
    country = Column(String, nullable=True)
    region = Column(String, nullable=True)
    city = Column(String, nullable=True)
    location_source = Column(String, nullable=True)
    threat_score = Column(Integer, nullable=True)
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
