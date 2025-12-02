"""
Subscription Management Routes
-----------------------------
API endpoints for managing user subscriptions, usage tracking, and billing.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..core.utils import now_utc

from ..dependencies import get_db, get_current_user
from ..models.user import User
from ..core.pricing import PricingService, PricingTier
from ..services.usage_tracking import UsageTrackingService, PricingValidationService
from ..schemas.subscription import (
    SubscriptionInfoOut, 
    UsageStatsOut, 
    PricingPlansOut,
    SubscriptionUpdateRequest,
    UsageAnalyticsOut,
    TierRecommendationOut
)

router = APIRouter()


@router.get("/plans", response_model=PricingPlansOut)
def get_pricing_plans():
    """Get all available pricing plans."""
    plans = PricingService.get_public_plans()
    
    return PricingPlansOut(
        plans=plans,
        currency="USD",
        updated_at=now_utc()
    )


@router.get("/current", response_model=SubscriptionInfoOut)
def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription information."""
    usage_service = UsageTrackingService(db)
    usage_info = usage_service.get_user_current_usage(current_user)
    
    # Get plan details
    try:
        tier = PricingTier(current_user.subscription_tier)
    except ValueError:
        tier = PricingTier.STARTER
    plan = PricingService.get_plan(tier)
    
    return SubscriptionInfoOut(
        user_id=current_user.id,
        tier=current_user.subscription_tier,
        plan_name=plan.name,
        status=current_user.subscription_status,
        subscription_status=current_user.subscription_status,
        billing_cycle=current_user.billing_cycle,
        price_monthly=plan.price_monthly,
        price_yearly=plan.price_yearly,
        subscription_start_date=current_user.subscription_start_date,
        subscription_end_date=current_user.subscription_end_date,
        trial_ends_at=current_user.trial_ends_at,
        current_period_start=current_user.current_period_start,
        next_billing_date=usage_info["next_reset_date"],
        stripe_customer_id=current_user.stripe_customer_id,
        stripe_subscription_id=current_user.stripe_subscription_id,
        usage_info=usage_info,
        features=plan.features,
        upgrade_available=usage_info["upgrade_available"]
    )


@router.get("/usage", response_model=UsageStatsOut)
def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed usage statistics for current user."""
    usage_service = UsageTrackingService(db)
    usage_info = usage_service.get_user_current_usage(current_user)

    payload = {
        "user_id": current_user.id,
        "subscription_status": current_user.subscription_status,
        "trial_ends_at": current_user.trial_ends_at,
        **usage_info,
    }

    return UsageStatsOut(**payload)


@router.get("/analytics", response_model=UsageAnalyticsOut)
def get_usage_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage analytics for the specified period."""
    usage_service = UsageTrackingService(db)
    analytics = usage_service.get_usage_analytics(current_user, days)
    
    return UsageAnalyticsOut(
        user_id=current_user.id,
        **analytics
    )


@router.get("/recommendation", response_model=Optional[TierRecommendationOut])
def get_tier_recommendation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-powered tier recommendation based on usage patterns."""
    usage_service = UsageTrackingService(db)
    recommendation = usage_service.get_tier_recommendation(current_user)
    
    if recommendation:
        return TierRecommendationOut(
            user_id=current_user.id,
            current_tier=current_user.subscription_tier,
            **recommendation
        )
    
    return None


@router.post("/upgrade")
def initiate_subscription_upgrade(
    upgrade_request: SubscriptionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate subscription upgrade process."""
    # Validate target tier
    try:
        target_tier = PricingTier(upgrade_request.target_tier)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid pricing tier: {upgrade_request.target_tier}"
        )
    
    current_tier = PricingTier(current_user.subscription_tier)
    
    # Validate upgrade path
    upgrade_suggestions = PricingService.get_upgrade_suggestions(current_tier)
    if target_tier not in upgrade_suggestions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid upgrade path from {current_tier.value} to {target_tier.value}"
        )
    
    target_plan = PricingService.get_plan(target_tier)
    
    # For now, return upgrade information (Stripe integration would go here)
    return {
        "message": "Upgrade initiated",
        "current_tier": current_user.subscription_tier,
        "target_tier": target_tier.value,
        "target_plan": target_plan.name,
        "price_change": target_plan.price_monthly - PricingService.get_plan(current_tier).price_monthly,
        "billing_cycle": upgrade_request.billing_cycle,
        "effective_immediately": True,
        "next_steps": [
            "Payment processing will be handled by Stripe",
            "Subscription will be upgraded immediately upon successful payment",
            "New limits will take effect immediately"
        ]
        # TODO: Integrate with Stripe for actual payment processing
    }


@router.post("/downgrade")
def initiate_subscription_downgrade(
    downgrade_request: SubscriptionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate subscription downgrade process."""
    # Validate target tier
    try:
        target_tier = PricingTier(downgrade_request.target_tier)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid pricing tier: {downgrade_request.target_tier}"
        )
    
    current_tier = PricingTier(current_user.subscription_tier)
    target_plan = PricingService.get_plan(target_tier)
    current_plan = PricingService.get_plan(current_tier)
    
    # Check if downgrade is valid (target tier should have lower price)
    if target_plan.price_monthly >= current_plan.price_monthly:
        raise HTTPException(
            status_code=400,
            detail="Target tier is not a downgrade from current tier"
        )
    
    # Check if current usage fits in target tier
    usage_service = UsageTrackingService(db)
    usage_info = usage_service.get_user_current_usage(current_user)
    
    if usage_info["submissions_used"] > target_plan.monthly_submissions:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Usage exceeds target tier limits",
                "current_usage": usage_info["submissions_used"],
                "target_limit": target_plan.monthly_submissions,
                "message": f"Your current usage ({usage_info['submissions_used']} submissions) exceeds the limit for {target_plan.name} ({target_plan.monthly_submissions} submissions)"
            }
        )
    
    return {
        "message": "Downgrade initiated",
        "current_tier": current_user.subscription_tier,
        "target_tier": target_tier.value,
        "target_plan": target_plan.name,
        "savings": current_plan.price_monthly - target_plan.price_monthly,
        "billing_cycle": downgrade_request.billing_cycle,
        "effective_date": "End of current billing period",
        "next_steps": [
            "Downgrade will take effect at the end of your current billing period",
            "You'll retain current features until the effective date",
            "Billing will be adjusted automatically"
        ]
        # TODO: Integrate with Stripe for actual subscription modification
    }


@router.post("/cancel")
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel current subscription."""
    if current_user.subscription_tier == PricingTier.FREE.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel free tier subscription"
        )
    
    # Set subscription status to cancelled but keep active until period end
    current_user.subscription_status = "cancelled"
    db.commit()
    
    return {
        "message": "Subscription cancelled",
        "current_tier": current_user.subscription_tier,
        "status": "cancelled",
        "active_until": current_user.subscription_end_date,
        "downgrade_to": "free",
        "next_steps": [
            "Your subscription will remain active until the end of the current billing period",
            "You'll be downgraded to the free tier after expiration",
            "All data will be preserved"
        ]
    }


@router.post("/reactivate")
def reactivate_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reactivate a cancelled subscription."""
    if current_user.subscription_status != "cancelled":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reactivate subscription with status: {current_user.subscription_status}"
        )
    
    # Reactivate subscription
    current_user.subscription_status = "active"
    current_user.subscription_end_date = None  # Remove end date
    db.commit()
    
    return {
        "message": "Subscription reactivated",
        "tier": current_user.subscription_tier,
        "status": "active",
        "billing_cycle": current_user.billing_cycle
    }


@router.get("/billing-history")
def get_billing_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get billing history for the current user."""
    # TODO: Integrate with Stripe to fetch actual billing history
    return {
        "message": "Billing history endpoint",
        "user_id": current_user.id,
        "stripe_customer_id": current_user.stripe_customer_id,
        "note": "This endpoint will be implemented with Stripe integration",
        "billing_history": []
    }


@router.post("/validate-feature")
def validate_feature_access(
    feature: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate if user has access to a specific feature."""
    validation_service = PricingValidationService(db)
    
    try:
        validation_service.validate_feature_access(current_user, feature)
        return {
            "has_access": True,
            "feature": feature,
            "tier": current_user.subscription_tier
        }
    except HTTPException as e:
        return {
            "has_access": False,
            "feature": feature,
            "tier": current_user.subscription_tier,
            "error": e.detail
        }
