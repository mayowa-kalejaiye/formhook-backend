"""
User model definition.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    api_token_hash = Column(String, nullable=True)
    token_created_at = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, default=False)
    
    # Subscription and Pricing
    subscription_tier = Column(String, default="starter", nullable=False)  # PricingTier enum value
    subscription_status = Column(String, default="trialing", nullable=False)  # trialing, active, cancelled, suspended
    subscription_start_date = Column(DateTime(timezone=True), server_default=func.now())
    subscription_end_date = Column(DateTime(timezone=True), nullable=True)
    billing_cycle = Column(String, default="monthly", nullable=False)  # monthly, yearly
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage Tracking
    current_period_start = Column(DateTime(timezone=True), server_default=func.now())
    current_period_submissions = Column(Integer, default=0, nullable=False)
    total_submissions = Column(Integer, default=0, nullable=False)
    
    # Payment Information (for future Stripe integration)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    
    # Additional Metadata
    usage_metadata = Column(JSON, nullable=True)  # Store additional usage stats
    subscription_metadata = Column(JSON, nullable=True)  # Store subscription details
    
    # Relationships
    email_verifications = relationship("EmailVerification", back_populates="user")
    forms = relationship("Form", back_populates="user")
    push_subscriptions = relationship("PushSubscription", back_populates="user", cascade="all, delete-orphan")
    
    def reset_monthly_usage(self):
        """Reset monthly usage counter (called at billing cycle start)."""
        self.current_period_submissions = 0
        self.current_period_start = func.now()
    
    def increment_submission_count(self):
        """Increment submission counters."""
        self.current_period_submissions += 1
        self.total_submissions += 1
