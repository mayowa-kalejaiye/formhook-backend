"""
Dashboard summary endpoint for FormHook.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..dependencies import get_db, get_current_user
from ..models import form as form_model, submission as submission_model, webhook_delivery as webhook_model
from ..schemas.submission import SubmissionOut
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/dashboard/summary", tags=["Dashboard"])
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    days: int = 30
):
    """
    Returns dashboard summary for the current user:
    - Total forms count
    - Total submissions count
    - Recent activity (last 5 submissions)
    - Trend data for the selected range (default 30 days)
    - Webhook stats
    """
    # Total forms
    total_forms = db.query(form_model.Form).filter(form_model.Form.user_id == current_user.id).count()
    # Total submissions
    form_ids = db.query(form_model.Form.id).filter(form_model.Form.user_id == current_user.id).subquery()
    total_submissions = db.query(submission_model.Submission).filter(submission_model.Submission.form_id.in_(form_ids)).count()
    # Recent activity
    recent_submissions = (
        db.query(submission_model.Submission)
        .filter(submission_model.Submission.form_id.in_(form_ids))
        .order_by(submission_model.Submission.created_at.desc())
        .limit(5)
        .all()
    )
    # Trend data (submissions per day)
    date_from = datetime.utcnow() - timedelta(days=days)
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
        {"date": (datetime.utcnow() - timedelta(days=i)).date().isoformat(), "count": trend_counter.get((datetime.utcnow() - timedelta(days=i)).date(), 0)}
        for i in range(days-1, -1, -1)
    ]
    # Webhook stats
    webhook_stats = db.query(webhook_model.WebhookDelivery).filter(webhook_model.WebhookDelivery.form_id.in_(form_ids)).all()
    total_webhooks = len(webhook_stats)
    delivered = sum(1 for w in webhook_stats if w.status == "delivered")
    failed = sum(1 for w in webhook_stats if w.status == "failed")
    pending = sum(1 for w in webhook_stats if w.status == "pending")
    return {
        "total_forms": total_forms,
        "total_submissions": total_submissions,
        "recent_submissions": [SubmissionOut.from_orm(s) for s in recent_submissions],
        "trend": trend_data,
        "webhook_stats": {
            "total": total_webhooks,
            "delivered": delivered,
            "failed": failed,
            "pending": pending
        }
    }
