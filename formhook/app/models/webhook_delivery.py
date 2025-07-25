"""
Model for tracking webhook delivery attempts and retries.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base

class WebhookDelivery(Base):
    __tablename__ = "webhook_delivery"
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    webhook_url = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PENDING")  # PENDING, SUCCESS, FAILED
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime(timezone=True))
    next_retry_at = Column(DateTime(timezone=True))
    response_code = Column(Integer, nullable=True)
    error_message = Column(String, nullable=True)
    submission = relationship("Submission", backref="webhook_deliveries")
