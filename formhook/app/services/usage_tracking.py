"""
Usage Tracking Service
---------------------
Service for tracking and validating user usage against pricing tier limits.
Handles submission counting, limit enforcement, and overage calculations.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..models.user import User
from ..models.submission import Submission
from ..models.form import Form
from ..core.pricing import PricingService, PricingTier
from ..core.utils import now_utc
from fastapi import HTTPException


class UsageTrackingService:
    """Service for tracking and managing user usage."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_current_usage(self, user: User) -> Dict[str, Any]:
        """Return an authoritative usage snapshot for the user's active billing cycle."""
        submissions_used, period_start, next_reset, lifetime_submissions, forms_count = self._compute_cycle_usage(user)

        tier = self._resolve_pricing_tier(user.subscription_tier)
        plan = PricingService.get_plan(tier)
        billing_cycle = (user.billing_cycle or "monthly").lower()

        submissions_limit = plan.monthly_submissions
        submissions_remaining = max(0, submissions_limit - submissions_used)
        usage_percentage = round((submissions_used / submissions_limit) * 100, 2) if submissions_limit else 0.0
        is_over_limit = submissions_used > submissions_limit

        overage_cost = PricingService.calculate_overage_cost(tier, submissions_used)
        plan_price_cents = plan.price_yearly if billing_cycle == "yearly" else plan.price_monthly
        plan_price = PricingService.format_price(plan_price_cents)

        now = now_utc()
        days_remaining = max(0, int((next_reset - now).total_seconds() // 86400))
        upgrade_available = bool(PricingService.get_upgrade_suggestions(tier))

        return {
            "current_tier": tier.value,
            "billing_cycle": billing_cycle,
            "current_period_start": period_start,
            "next_reset_date": next_reset,
            "days_remaining": days_remaining,

            # Usage stats
            "submissions_used": submissions_used,
            "submissions_limit": submissions_limit,
            "submissions_remaining": submissions_remaining,
            "usage_percentage": usage_percentage,
            "is_over_limit": is_over_limit,
            "total_submissions": lifetime_submissions,

            # Forms
            "forms_count": forms_count,
            "forms_limit": plan.max_forms,

            # Financial
            "overage_cost_cents": overage_cost,
            "overage_cost_formatted": PricingService.format_price(overage_cost),

            # Plan details
            "plan_name": plan.name,
            "plan_price": plan_price,
            "upgrade_available": upgrade_available,
        }
    
    def can_user_submit_form(self, user: User) -> Tuple[bool, Optional[str]]:
        """
        Check if user can submit another form based on their tier limits.
        Returns (can_submit, error_message)
        """
        submissions_used, _, _, _, _ = self._compute_cycle_usage(user)
        tier = self._resolve_pricing_tier(user.subscription_tier)
        plan = PricingService.get_plan(tier)
        
        # Check if user is over their monthly limit
        if submissions_used >= plan.monthly_submissions:
            # For free tier, enforce hard limits
            if tier == PricingTier.FREE:
                return False, f"Monthly submission limit reached ({plan.monthly_submissions}). Please upgrade to continue."
            
            # For paid tiers, allow overage but warn
            overage_cost = PricingService.calculate_overage_cost(
                tier,
                submissions_used + 1
            )
            
            warning = f"You're over your monthly limit. Additional submissions will incur overage charges."
            if overage_cost > 0:
                cost_per_submission = PricingService.calculate_overage_cost(
                    tier,
                    1
                )
                warning += f" Next submission will cost {PricingService.format_price(cost_per_submission)}."
            
            return True, warning
        
        return True, None
    
    def can_user_create_form(self, user: User) -> Tuple[bool, Optional[str]]:
        """
        Check if user can create another form based on their tier limits.
        Returns (can_create, error_message)
        """
        self._ensure_usage_defaults(user)
        plan = PricingService.get_plan(PricingTier(user.subscription_tier))
        
        # Check form limits
        if plan.max_forms is not None:  # None means unlimited
            current_forms = self.db.query(func.count()).select_from(
                self.db.query(user).join("forms").subquery()
            ).scalar() or 0
            
            if current_forms >= plan.max_forms:
                return False, f"Form limit reached ({plan.max_forms}). Please upgrade to create more forms."
        
        return True, None
    
    def record_submission(self, user: User) -> None:
        """Record a form submission for the user."""
        self._ensure_usage_defaults(user)
        user.increment_submission_count()
        self.db.commit()
    
    def get_usage_analytics(self, user: User, days: int = 30) -> Dict[str, Any]:
        """Get detailed usage analytics for a user."""
        end_date = now_utc()
        start_date = end_date - timedelta(days=days)
        
        # Get submission history
        submissions = self.db.query(Submission).filter(
            and_(
                Submission.user_id == user.id,
                Submission.created_at >= start_date,
                Submission.created_at <= end_date
            )
        ).all()
        
        # Group by day
        daily_usage = {}
        for submission in submissions:
            day = submission.created_at.date().isoformat()
            daily_usage[day] = daily_usage.get(day, 0) + 1
        
        # Calculate trends
        total_submissions = len(submissions)
        avg_daily = total_submissions / days if days > 0 else 0
        
        # Peak usage day
        peak_day = max(daily_usage.items(), key=lambda x: x[1]) if daily_usage else None
        
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_submissions": total_submissions,
            "average_daily": round(avg_daily, 2),
            "peak_day": {
                "date": peak_day[0],
                "submissions": peak_day[1]
            } if peak_day else None,
            "daily_breakdown": daily_usage,
            "current_tier": user.subscription_tier,
            "usage_efficiency": self._calculate_usage_efficiency(user)
        }
    
    def get_tier_recommendation(self, user: User) -> Optional[Dict[str, Any]]:
        """Analyze usage and recommend optimal pricing tier."""
        usage = self.get_user_current_usage(user)
        current_tier = self._resolve_pricing_tier(user.subscription_tier)
        
        # If user is consistently under 50% usage, suggest downgrade
        if usage["usage_percentage"] < 50 and current_tier != PricingTier.FREE:
            # Find lower tier that still accommodates usage
            all_tiers = [PricingTier.FREE, PricingTier.STARTER, PricingTier.PROFESSIONAL, PricingTier.BUSINESS]
            for tier in reversed(all_tiers):
                if tier.value == user.subscription_tier:
                    break
                plan = PricingService.get_plan(tier)
                if plan.monthly_submissions >= usage["submissions_used"]:
                    monthly_savings = PricingService.get_plan(current_tier).price_monthly - plan.price_monthly
                    return {
                        "type": "downgrade",
                        "recommended_tier": tier.value,
                        "reason": f"Your usage is only {usage['usage_percentage']:.1f}% of your current plan",
                        "monthly_savings": PricingService.format_price(monthly_savings),
                        "plan_name": plan.name
                    }
        
        # If user is over 80% usage or over limit, suggest upgrade
        if usage["usage_percentage"] > 80 or usage["is_over_limit"]:
            upgrade_options = PricingService.get_upgrade_suggestions(current_tier)
            if upgrade_options:
                next_tier = upgrade_options[0]
                next_plan = PricingService.get_plan(next_tier)
                monthly_cost = next_plan.price_monthly - PricingService.get_plan(current_tier).price_monthly
                
                return {
                    "type": "upgrade",
                    "recommended_tier": next_tier.value,
                    "reason": f"You're using {usage['usage_percentage']:.1f}% of your current plan",
                    "monthly_cost": PricingService.format_price(monthly_cost),
                    "plan_name": next_plan.name,
                    "additional_submissions": next_plan.monthly_submissions - PricingService.get_plan(current_tier).monthly_submissions
                }
        
        return None
    
    def _calculate_usage_efficiency(self, user: User) -> float:
        """Calculate how efficiently the user is using their plan (0-100%)."""
        plan = PricingService.get_plan(self._resolve_pricing_tier(user.subscription_tier))
        if plan.monthly_submissions == 0:
            return 100.0

        submissions_used, *_ = self._compute_cycle_usage(user)
        return min(100.0, (submissions_used / plan.monthly_submissions) * 100)

    def _ensure_usage_defaults(self, user: User) -> None:
        """Ensure subscription tier, billing cycle, and usage counters have sane defaults."""
        updated = False

        tier_value = (user.subscription_tier or PricingTier.FREE.value).lower()
        try:
            resolved_tier = PricingTier(tier_value)
        except ValueError:
            resolved_tier = PricingTier.FREE
        if user.subscription_tier != resolved_tier.value:
            user.subscription_tier = resolved_tier.value
            updated = True

        billing_cycle = (user.billing_cycle or "monthly").lower()
        if billing_cycle not in ("monthly", "yearly"):
            billing_cycle = "monthly"
        if user.billing_cycle != billing_cycle:
            user.billing_cycle = billing_cycle
            updated = True

        if user.current_period_start is None:
            user.current_period_start = now_utc()
            updated = True

        if user.current_period_submissions is None:
            user.current_period_submissions = 0
            updated = True

        if updated:
            self.db.commit()
            self.db.refresh(user)

    def _resolve_pricing_tier(self, tier_value: Optional[str]) -> PricingTier:
        """Normalize arbitrary tier strings to a valid PricingTier (default to FREE)."""
        if not tier_value:
            return PricingTier.FREE
        try:
            return PricingTier(tier_value.lower())
        except ValueError:
            return PricingTier.FREE

    def _compute_cycle_usage(self, user: User) -> Tuple[int, datetime, datetime, int, int]:
        """Compute usage statistics for the active billing cycle.

        Returns a tuple of (submissions_used, period_start, next_reset, lifetime_submissions, forms_count).
        """
        self._ensure_usage_defaults(user)
        now = now_utc()
        interval = self._get_billing_interval(user.billing_cycle)

        forms_count = self._get_forms_count(user)
        lifetime_submissions, first_submission_at = self._get_submission_stats(user, forms_count)

        anchor = user.current_period_start or user.subscription_start_date or user.created_at or now
        if first_submission_at and (anchor is None or first_submission_at < anchor):
            anchor = first_submission_at
        if anchor > now:
            anchor = now - interval

        elapsed = now - anchor
        completed_cycles = int(elapsed.total_seconds() // interval.total_seconds()) if elapsed.total_seconds() > 0 else 0
        period_start = anchor + (interval * completed_cycles)
        if period_start > now:
            period_start -= interval
        while now - period_start >= interval:
            period_start += interval

        next_reset = period_start + interval
        submissions_used = self._count_user_submissions(user, period_start, next_reset)

        updated = False
        if user.total_submissions != lifetime_submissions:
            user.total_submissions = lifetime_submissions
            updated = True
        if user.current_period_submissions != submissions_used or user.current_period_start != period_start:
            user.current_period_submissions = submissions_used
            user.current_period_start = period_start
            updated = True
        if updated:
            self.db.commit()
            self.db.refresh(user)

        return submissions_used, period_start, next_reset, lifetime_submissions, forms_count

    def _get_billing_interval(self, billing_cycle: Optional[str]) -> timedelta:
        cycle = (billing_cycle or "monthly").lower()
        return timedelta(days=365 if cycle == "yearly" else 30)

    def _get_forms_count(self, user: User) -> int:
        return self.db.query(func.count(Form.id)).filter(Form.user_id == user.id).scalar() or 0

    def _get_submission_stats(self, user: User, forms_count: int) -> Tuple[int, Optional[datetime]]:
        if forms_count == 0:
            return 0, None

        total_submissions, first_submission_at = (
            self.db
            .query(func.count(Submission.id), func.min(Submission.created_at))
            .join(Form, Submission.form_id == Form.id)
            .filter(Form.user_id == user.id)
            .one()
        )
        return (total_submissions or 0), first_submission_at

    def _count_user_submissions(self, user: User, start: datetime, end: datetime) -> int:
        query = (
            self.db
            .query(func.count(Submission.id))
            .join(Form, Submission.form_id == Form.id)
            .filter(Form.user_id == user.id)
        )
        if start:
            query = query.filter(Submission.created_at >= start)
        if end:
            query = query.filter(Submission.created_at < end)
        return query.scalar() or 0


class PricingValidationService:
    """Service for validating user actions against pricing tier restrictions."""
    
    def __init__(self, db: Session):
        self.db = db
        self.usage_service = UsageTrackingService(db)
    
    def validate_form_submission(self, user: User) -> None:
        """Validate that user can submit a form. Raises HTTPException if not allowed."""
        can_submit, message = self.usage_service.can_user_submit_form(user)
        
        if not can_submit:
            upgrade_suggestions = PricingService.get_upgrade_suggestions(PricingTier(user.subscription_tier))
            upgrade_info = {}
            
            if upgrade_suggestions:
                next_tier = upgrade_suggestions[0]
                next_plan = PricingService.get_plan(next_tier)
                upgrade_info = {
                    "upgrade_tier": next_tier.value,
                    "upgrade_name": next_plan.name,
                    "upgrade_price": PricingService.format_price(next_plan.price_monthly),
                    "upgrade_submissions": next_plan.monthly_submissions
                }
            
            raise HTTPException(
                status_code=402,  # Payment Required
                detail={
                    "error": "Usage limit exceeded",
                    "message": message,
                    "current_tier": user.subscription_tier,
                    "usage_info": self.usage_service.get_user_current_usage(user),
                    "upgrade_options": upgrade_info
                }
            )
    
    def validate_form_creation(self, user: User) -> None:
        """Validate that user can create a form. Raises HTTPException if not allowed."""
        can_create, message = self.usage_service.can_user_create_form(user)
        
        if not can_create:
            upgrade_suggestions = PricingService.get_upgrade_suggestions(PricingTier(user.subscription_tier))
            upgrade_info = {}
            
            if upgrade_suggestions:
                next_tier = upgrade_suggestions[0]
                next_plan = PricingService.get_plan(next_tier)
                upgrade_info = {
                    "upgrade_tier": next_tier.value,
                    "upgrade_name": next_plan.name,
                    "upgrade_price": PricingService.format_price(next_plan.price_monthly),
                    "upgrade_forms": "Unlimited" if next_plan.max_forms is None else next_plan.max_forms
                }
            
            raise HTTPException(
                status_code=402,  # Payment Required
                detail={
                    "error": "Form limit exceeded",
                    "message": message,
                    "current_tier": user.subscription_tier,
                    "upgrade_options": upgrade_info
                }
            )
    
    def validate_feature_access(self, user: User, feature: str) -> None:
        """Validate that user has access to a specific feature. Raises HTTPException if not allowed."""
        if not PricingService.can_user_access_feature(PricingTier(user.subscription_tier), feature):
            plan = PricingService.get_plan(PricingTier(user.subscription_tier))
            
            # Find which tier includes this feature
            required_tier = None
            for tier in [PricingTier.STARTER, PricingTier.PROFESSIONAL, PricingTier.BUSINESS, PricingTier.ENTERPRISE]:
                if PricingService.can_user_access_feature(tier, feature):
                    required_tier = tier
                    break
            
            upgrade_info = {}
            if required_tier:
                required_plan = PricingService.get_plan(required_tier)
                upgrade_info = {
                    "required_tier": required_tier.value,
                    "required_name": required_plan.name,
                    "required_price": PricingService.format_price(required_plan.price_monthly)
                }
            
            raise HTTPException(
                status_code=402,  # Payment Required
                detail={
                    "error": "Feature not available",
                    "message": f"The '{feature}' feature is not available on your current plan ({plan.name})",
                    "current_tier": user.subscription_tier,
                    "feature": feature,
                    "upgrade_required": upgrade_info
                }
            )
