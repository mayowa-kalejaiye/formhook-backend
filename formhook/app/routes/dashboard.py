"""
Dashboard summary endpoint for FormHook.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, inspect, select
from ..dependencies import get_db, get_current_user
from ..models import form as form_model, submission as submission_model, webhook_delivery as webhook_model
from ..schemas.submission import SubmissionOut
from ..services.cache import cache
from datetime import timedelta
from ..core.utils import now_utc

router = APIRouter()


def _submission_select_columns(db: Session):
    inspector = inspect(db.get_bind())
    if not inspector.has_table("submissions"):
        return []

    existing = {column["name"] for column in inspector.get_columns("submissions")}
    required = ["id", "form_id", "data", "ip_address", "created_at"]
    optional = [
        "country",
        "region",
        "city",
        "location_source",
        "latitude",
        "longitude",
        "threat_score",
        "device_type",
        "user_agent",
    ]
    column_names = required + [name for name in optional if name in existing]
    return [submission_model.Submission.__table__.c[name] for name in column_names]

@router.get("/dashboard/summary", tags=["Dashboard"])
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    days: int = 30
):
    """
    Returns dashboard summary for the current user. Cached for 30 seconds.
    - Total forms count
    - Total submissions count
    - Recent activity (last 5 submissions)
    - Trend data for the selected range (default 30 days)
    - Webhook stats
    """
    # Try to get from cache
    cache_key = f"dashboard:{current_user.id}:days_{days}"
    cached_summary = cache.get(cache_key)
    if cached_summary is not None:
        return cached_summary
    # Total forms
    total_forms = db.query(form_model.Form).filter(form_model.Form.user_id == current_user.id).count()
    # Total submissions
    form_ids = db.query(form_model.Form.id).filter(form_model.Form.user_id == current_user.id).subquery()
    total_submissions = db.query(func.count(submission_model.Submission.id)).filter(submission_model.Submission.form_id.in_(form_ids)).scalar() or 0
    # Recent activity
    submission_columns = _submission_select_columns(db)
    recent_submissions = []
    if submission_columns:
        recent_submissions = db.execute(
            select(*submission_columns)
            .where(submission_model.Submission.form_id.in_(form_ids))
            .order_by(submission_model.Submission.created_at.desc())
            .limit(5)
        ).all()
    # Trend data (submissions per day)
    date_from = now_utc() - timedelta(days=days)
    trend = (
        db.query(
            submission_model.Submission.created_at,
        )
        .filter(
            submission_model.Submission.form_id.in_(form_ids),
            submission_model.Submission.created_at >= date_from
        )
        .all()
    )
    # Aggregate trend data by day
    from collections import Counter
    trend_counter = Counter(dt.created_at.date() for dt in trend)
    trend_data = [
        {"date": (now_utc() - timedelta(days=i)).date().isoformat(), "count": trend_counter.get((now_utc() - timedelta(days=i)).date(), 0)}
        for i in range(days-1, -1, -1)
    ]
    # Webhook stats - with error handling for missing table
    try:
        webhook_stats = db.query(webhook_model.WebhookDelivery).filter(webhook_model.WebhookDelivery.form_id.in_(form_ids)).all()
        total_webhooks = len(webhook_stats)
        delivered = sum(1 for w in webhook_stats if w.status == "delivered")
        failed = sum(1 for w in webhook_stats if w.status == "failed")
        pending = sum(1 for w in webhook_stats if w.status == "pending")
    except Exception as e:
        # If webhook_delivery table doesn't exist yet, return empty stats
        total_webhooks = 0
        delivered = 0
        failed = 0
        pending = 0
    
    summary = {
        "total_forms": total_forms,
        "total_submissions": total_submissions,
        "recent_submissions": [SubmissionOut(**dict(s._mapping)) for s in recent_submissions],
        "trend": trend_data,
        "webhook_stats": {
            "total": total_webhooks,
            "delivered": delivered,
            "failed": failed,
            "pending": pending
        }
    }
    
    # Cache the result for 30 seconds
    cache.set(cache_key, summary, ttl_seconds=30)
    
    return summary
