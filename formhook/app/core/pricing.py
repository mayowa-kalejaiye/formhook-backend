"""
FormHook Pricing Configuration System
------------------------------------
Centralized pricing tiers, limits, and feature definitions for the FormHook platform.
This module defines all pricing plans, usage limits, and feature flags.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json


class PricingTier(str, Enum):
    """Enumeration of available pricing tiers."""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


@dataclass
class PricingPlan:
    """Definition of a pricing plan with all limits and features."""
    tier: PricingTier
    name: str
    price_monthly: int  # Price in cents (e.g., 900 = $9.00)
    price_yearly: int   # Price in cents for yearly billing (with discount)
    
    # Usage Limits
    monthly_submissions: int
    max_forms: Optional[int]  # None = unlimited
    max_team_members: int
    file_upload_size_mb: int
    api_rate_limit_per_minute: int
    
    # Features
    features: List[str]
    
    # Support Level
    support_level: str
    sla_uptime: Optional[float]  # e.g., 0.999 for 99.9%
    
    # Branding
    remove_branding: bool
    white_label: bool
    
    def __post_init__(self):
        """Validate pricing plan configuration."""
        if self.price_monthly < 0:
            raise ValueError("Monthly price cannot be negative")
        if self.monthly_submissions <= 0:
            raise ValueError("Monthly submissions must be positive")
        if self.max_team_members <= 0:
            raise ValueError("Max team members must be positive")


# Define all pricing plans
PRICING_PLANS: Dict[PricingTier, PricingPlan] = {
    PricingTier.STARTER: PricingPlan(
        tier=PricingTier.STARTER,
        name="Free",
        price_monthly=0,
        price_yearly=0,
        monthly_submissions=1000,
        max_forms=25,
        max_team_members=1,
        file_upload_size_mb=5,
        api_rate_limit_per_minute=100,
        features=[
            "basic_analytics",
            "email_notifications",
            "api_access",
            "email_support",
            "basic_integrations",
            "remove_branding"
        ],
        support_level="email",
        sla_uptime=0.99,  # 99%
        remove_branding=True,
        white_label=False
    )
}


class PricingService:
    """Service class for pricing-related operations."""
    
    @staticmethod
    def get_plan(tier: PricingTier) -> PricingPlan:
        """Get pricing plan by tier."""
        return PRICING_PLANS.get(tier, PRICING_PLANS[PricingTier.STARTER])
    
    @staticmethod
    def get_all_plans() -> Dict[PricingTier, PricingPlan]:
        """Get all pricing plans."""
        return PRICING_PLANS.copy()
    
    @staticmethod
    def get_public_plans() -> Dict[str, Dict[str, Any]]:
        """Get pricing plans in a format suitable for public API responses."""
        plans = {}
        for tier, plan in PRICING_PLANS.items():
            plans[tier.value] = {
                "name": plan.name,
                "price_monthly": plan.price_monthly,
                "price_yearly": plan.price_yearly,
                "monthly_submissions": plan.monthly_submissions,
                "max_forms": plan.max_forms,
                "max_team_members": plan.max_team_members,
                "file_upload_size_mb": plan.file_upload_size_mb,
                "features": plan.features,
                "support_level": plan.support_level,
                "sla_uptime": plan.sla_uptime,
                "remove_branding": plan.remove_branding,
                "white_label": plan.white_label
            }
        return plans
    
    @staticmethod
    def can_user_access_feature(user_tier: PricingTier, feature: str) -> bool:
        """Check if a user's tier includes a specific feature."""
        plan = PricingService.get_plan(user_tier)
        return feature in plan.features
    
    @staticmethod
    def get_upgrade_suggestions(current_tier: PricingTier) -> List[PricingTier]:
        """Upgrade paths are disabled while billing is paused."""
        return []
    
    @staticmethod
    def calculate_overage_cost(tier: PricingTier, submissions_used: int) -> int:
        """Overage billing is disabled while running a free-only model."""
        return 0
    
    @staticmethod
    def format_price(price_cents: int) -> str:
        """Format price in cents to human-readable string."""
        if price_cents == 0:
            return "Free"
        
        dollars = price_cents // 100
        cents = price_cents % 100
        
        if cents == 0:
            return f"${dollars}"
        else:
            return f"${dollars}.{cents:02d}"


# Feature flags for easy access
FEATURES = {
    # Analytics
    "basic_analytics": "Basic form submission analytics",
    "advanced_analytics": "Advanced analytics with conversion tracking",
    "enterprise_analytics": "Enterprise analytics with custom reports",
    
    # Communication
    "email_notifications": "Email notifications for form submissions",
    
    # API Access
    "api_access": "REST API access",
    
    # Support
    "community_support": "Community forum support",
    "email_support": "Email support",
    "priority_email_support": "Priority email support",
    "phone_support": "Phone support",
    "dedicated_support": "Dedicated account manager",
    
    # Integrations
    "basic_integrations": "Basic third-party integrations",
    "advanced_integrations": "Advanced integrations (Zapier, webhooks)",
    "enterprise_integrations": "Enterprise integrations (SSO, custom APIs)",
    
    # Advanced Features
    "webhooks": "Real-time webhook notifications",
    "ab_testing": "A/B testing for forms",
    "custom_domains": "Custom domain support",
    "custom_fields": "Unlimited custom field types",
    "white_label": "White-label branding options",
    "remove_branding": "Remove FormHook branding",
    "priority_processing": "Priority form processing",
    "sso_integration": "Single Sign-On integration",
    "custom_integrations": "Custom integration development",
    "dedicated_infrastructure": "Dedicated infrastructure",
    "professional_services": "Professional services and consultation"
}


def get_feature_description(feature: str) -> str:
    """Get human-readable description of a feature."""
    return FEATURES.get(feature, feature)


# Export main components
__all__ = [
    'PricingTier',
    'PricingPlan', 
    'PricingService',
    'PRICING_PLANS',
    'FEATURES',
    'get_feature_description'
]
