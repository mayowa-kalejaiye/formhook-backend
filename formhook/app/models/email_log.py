"""
Model for logging sent emails for analytics.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base

class EmailLog(Base):
    __tablename__ = "email_logs"
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(String, ForeignKey("forms.id"), nullable=False)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    to_email = Column(String, nullable=False)
    status = Column(String, nullable=False, default="SENT")  # SENT, FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
