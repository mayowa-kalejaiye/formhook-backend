"""
Model to store idempotency keys mapping to submissions.
Prevents duplicate submissions when clients retry with the same Idempotency-Key.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import timedelta
from ..core.database import Base
from ..core.utils import now_utc


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String, nullable=False)
    form_id = Column(String, nullable=False)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    __table_args__ = (
        UniqueConstraint('key_hash', 'form_id', name='uq_idempotency_key_form'),
    )

    submission = relationship("Submission")
