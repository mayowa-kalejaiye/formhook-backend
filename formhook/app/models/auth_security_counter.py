"""
Persistent counters for auth security telemetry.
"""

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from ..core.database import Base
from ..core.utils import now_utc


class AuthSecurityCounter(Base):
    __tablename__ = "auth_security_counters"
    __table_args__ = (
        UniqueConstraint("endpoint", "email", "ip_address", name="uq_auth_security_counter_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(64), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(64), nullable=False, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)
