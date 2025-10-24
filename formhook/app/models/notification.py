"""
Notification model definition.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from ..core.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(20), nullable=False, index=True)  # submission, webhook, system, email, security, milestone
    priority = Column(String(10), nullable=False)  # low, medium, high, urgent
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    read = Column(Boolean, default=False, nullable=False, index=True)
    archived = Column(Boolean, default=False, nullable=False, index=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="notifications")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    email_notifications = Column(Boolean, default=True, nullable=False)
    webhook_failures = Column(Boolean, default=True, nullable=False)
    security_alerts = Column(Boolean, default=True, nullable=False)
    milestone_alerts = Column(Boolean, default=True, nullable=False)
    submission_alerts = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="notification_preferences", uselist=False)
