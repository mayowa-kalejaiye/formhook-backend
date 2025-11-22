"""
Email verification model for FormHook.
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import timedelta
from ..core.utils import now_utc
import uuid

from ..core.database import Base

class EmailVerification(Base):
    __tablename__ = "email_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=now_utc)
    expires_at = Column(DateTime, default=lambda: now_utc() + timedelta(hours=24))
    is_used = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="email_verifications")
