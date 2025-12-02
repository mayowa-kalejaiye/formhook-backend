"""
Subscription and Usage Tracking Schemas
--------------------------------------
Pydantic schemas for subscription management, usage tracking, and billing endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class BillingCycle(str, Enum):
    """Billing cycle options."""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    """Subscription status options."""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class SubscriptionInfoOut(BaseModel):
    """User subscription information response."""
    user_id: int
    tier: str
    plan_name: str
    status: str
    subscription_status: str
    billing_cycle: str
    price_monthly: int  # In cents
    price_yearly: int   # In cents
    subscription_start_date: datetime
    subscription_end_date: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    current_period_start: datetime
    next_billing_date: datetime
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    usage_info: Dict[str, Any]
    features: List[str]
    upgrade_available: bool

    class Config:
        from_attributes = True


class UsageStatsOut(BaseModel):
    """User usage statistics response."""
    user_id: int
    current_tier: str
    subscription_status: str
    billing_cycle: str
    current_period_start: datetime
    next_reset_date: datetime
    days_remaining: int
    trial_ends_at: Optional[datetime] = None
    
    # Usage statistics
    submissions_used: int
    submissions_limit: int
    submissions_remaining: int
    usage_percentage: float
    is_over_limit: bool
    total_submissions: int
    
    # Form statistics
    forms_count: int
    forms_limit: Optional[int] = None
    
    # Financial information
    overage_cost_cents: int
    overage_cost_formatted: str
    
    # Plan information
    plan_name: str
    plan_price: str
    upgrade_available: bool

    class Config:
        from_attributes = True


class UsageAnalyticsOut(BaseModel):
    """Detailed usage analytics response."""
    user_id: int
    period_days: int
    start_date: str  # ISO format
    end_date: str    # ISO format
    total_submissions: int
    average_daily: float
    peak_day: Optional[Dict[str, Any]] = None
    daily_breakdown: Dict[str, int]
    current_tier: str
    usage_efficiency: float

    class Config:
        from_attributes = True


class TierRecommendationOut(BaseModel):
    """AI-powered tier recommendation response."""
    user_id: int
    current_tier: str
    type: str  # "upgrade" or "downgrade"
    recommended_tier: str
    reason: str
    plan_name: str
    
    # Financial impact
    monthly_savings: Optional[str] = None    # For downgrades
    monthly_cost: Optional[str] = None       # For upgrades
    additional_submissions: Optional[int] = None  # For upgrades

    class Config:
        from_attributes = True


class PricingPlansOut(BaseModel):
    """All pricing plans response."""
    plans: Dict[str, Dict[str, Any]]
    currency: str = "USD"
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionUpdateRequest(BaseModel):
    """Request to update subscription tier."""
    target_tier: str = Field(..., description="Target pricing tier")
    billing_cycle: BillingCycle = Field(
        BillingCycle.MONTHLY, 
        description="Billing cycle for new subscription"
    )
    
    @validator('target_tier')
    def validate_tier(cls, v):
        valid_tiers = ['starter', 'professional', 'business', 'enterprise']
        if v.lower() not in valid_tiers:
            raise ValueError(f'Invalid tier. Must be one of: {valid_tiers}')
        return v.lower()


class FeatureValidationRequest(BaseModel):
    """Request to validate feature access."""
    feature: str = Field(..., description="Feature name to validate")


class FeatureValidationResponse(BaseModel):
    """Response for feature validation."""
    has_access: bool
    feature: str
    tier: str
    error: Optional[Dict[str, Any]] = None


class BillingHistoryOut(BaseModel):
    """Billing history response."""
    user_id: int
    stripe_customer_id: Optional[str] = None
    invoices: List[Dict[str, Any]] = []
    total_spent: int = 0  # In cents
    currency: str = "USD"

    class Config:
        from_attributes = True


class OverageWarning(BaseModel):
    """Overage warning information."""
    is_over_limit: bool
    overage_amount: int
    overage_cost_cents: int
    overage_cost_formatted: str
    warning_message: str
    upgrade_suggestion: Optional[Dict[str, Any]] = None


class SubscriptionLimitsOut(BaseModel):
    """Current subscription limits and usage."""
    user_id: int
    tier: str
    
    # Limits
    monthly_submissions_limit: int
    forms_limit: Optional[int] = None
    team_members_limit: int
    file_upload_size_mb: int
    api_rate_limit_per_minute: int
    
    # Current usage
    current_submissions: int
    current_forms: int
    current_team_members: int
    
    # Status
    submissions_remaining: int
    forms_remaining: Optional[int] = None
    can_create_forms: bool
    can_submit_forms: bool
    
    # Warnings
    overage_warning: Optional[OverageWarning] = None

    class Config:
        from_attributes = True


# Export all schemas
__all__ = [
    'BillingCycle',
    'SubscriptionStatus', 
    'SubscriptionInfoOut',
    'UsageStatsOut',
    'UsageAnalyticsOut',
    'TierRecommendationOut',
    'PricingPlansOut',
    'SubscriptionUpdateRequest',
    'FeatureValidationRequest',
    'FeatureValidationResponse',
    'BillingHistoryOut',
    'OverageWarning',
    'SubscriptionLimitsOut'
]
