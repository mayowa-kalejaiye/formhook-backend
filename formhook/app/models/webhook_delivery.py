"""
Model for tracking webhook delivery attempts and retries.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects import postgresql
from ..core.database import Base

class WebhookDelivery(Base):
    __tablename__ = "webhook_delivery"
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(String, index=True)  # UUID as string for compatibility
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    webhook_url = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PENDING")  # PENDING, SUCCESS, FAILED
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime(timezone=True))
    next_retry_at = Column(DateTime(timezone=True))
    response_code = Column(Integer, nullable=True)
    error_message = Column(String, nullable=True)
    success = Column(Integer, nullable=True)
    headers_sent = Column(postgresql.JSONB, nullable=True)
    response_body = Column(String, nullable=True)
    retry_count = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    submission = relationship("Submission", backref="webhook_deliveries")
