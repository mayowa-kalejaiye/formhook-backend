"""
Push Subscription model for browser push notifications
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .user import Base


class PushSubscription(Base):
    """
    Store browser push notification subscriptions
    """
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(Text, nullable=False, unique=True)  # Push service endpoint
    p256dh = Column(Text, nullable=False)  # Encryption key
    auth = Column(Text, nullable=False)  # Authentication secret
    user_agent = Column(Text, nullable=True)  # Browser info
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    user = relationship("User", back_populates="push_subscriptions")

    # Indexes for performance
    __table_args__ = (
        Index('ix_push_subscriptions_user_id', 'user_id'),
        Index('ix_push_subscriptions_endpoint', 'endpoint'),
        Index('ix_push_subscriptions_last_used', 'last_used'),
    )

    def __repr__(self):
        return f"<PushSubscription(id={self.id}, user_id={self.user_id}, endpoint={self.endpoint[:50]}...)>"
