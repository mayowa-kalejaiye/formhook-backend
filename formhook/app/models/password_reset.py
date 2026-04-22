"""
Password reset token model for FormHook.
"""
from datetime import timedelta

import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..core.database import Base
from ..core.utils import now_utc


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=now_utc, nullable=False)
    expires_at = Column(DateTime, default=lambda: now_utc() + timedelta(hours=1), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="password_resets")