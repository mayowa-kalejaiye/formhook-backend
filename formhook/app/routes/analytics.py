"""
Analytics endpoint for form submissions, webhooks, emails, and unique IPs.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, extract
from datetime import datetime, timedelta
from typing import List, Optional
from ..dependencies import get_db, get_current_user
from ..models.form import Form
from ..models.submission import Submission
from ..models.webhook_delivery import WebhookDelivery
from ..models.email_log import EmailLog
from ..schemas.analytics import FormAnalyticsEntry, FormAnalyticsResponse

router = APIRouter()

@router.get("/forms/{form_id}/analytics", response_model=List[FormAnalyticsEntry], tags=["Forms"])
def form_analytics(
    form_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    interval: str = Query("day", regex="^(day|hour)$")
):
    # Validate form ownership
    form = db.query(Form).filter(Form.id == form_id, Form.user_id == current_user.id).first()
    if not form:
        raise HTTPException(status_code=403, detail="Not authorized to access this form.")

    # Date range
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    # Grouping logic
    if interval == "hour":
        date_expr = func.date_trunc('hour', Submission.created_at)
    else:
        date_expr = cast(Submission.created_at, Date)

    # Submissions per interval
    submissions_q = (
        db.query(date_expr.label("date"), func.count(Submission.id).label("submissions"))
        .filter(Submission.form_id == form_id, Submission.created_at >= date_from, Submission.created_at <= date_to)
        .group_by(date_expr)
    )
    submissions_map = {row.date.isoformat(): row.submissions for row in submissions_q}

    # Failed webhooks per interval
    webhook_q = (
        db.query(date_expr.label("date"), func.count(WebhookDelivery.id).label("failed_webhooks"))
        .join(Submission, WebhookDelivery.submission_id == Submission.id)
        .filter(Submission.form_id == form_id, WebhookDelivery.status == "failed", Submission.created_at >= date_from, Submission.created_at <= date_to)
        .group_by(date_expr)
    )
    webhook_map = {row.date.isoformat(): row.failed_webhooks for row in webhook_q}

    # Emails sent per interval
    email_q = (
        db.query(date_expr.label("date"), func.count(EmailLog.id).label("emails_sent"))
        .filter(EmailLog.form_id == form_id, EmailLog.status == "SENT", EmailLog.created_at >= date_from, EmailLog.created_at <= date_to)
        .group_by(date_expr)
    )
    email_map = {row.date.isoformat(): row.emails_sent for row in email_q}

    # Unique IPs per interval
    ip_q = (
        db.query(date_expr.label("date"), func.count(func.distinct(Submission.ip_address)).label("unique_ips"))
        .filter(Submission.form_id == form_id, Submission.created_at >= date_from, Submission.created_at <= date_to)
        .group_by(date_expr)
    )
    ip_map = {row.date.isoformat(): row.unique_ips for row in ip_q}

    # Build date range
    if interval == "hour":
        total_intervals = int((date_to - date_from).total_seconds() // 3600) + 1
        date_list = [(date_from + timedelta(hours=i)).replace(minute=0, second=0, microsecond=0) for i in range(total_intervals)]
    else:
        total_days = (date_to.date() - date_from.date()).days + 1
        date_list = [(date_from + timedelta(days=i)).date() for i in range(total_days)]

    # Compose response
    result = []
    for dt in date_list:
        key = dt.isoformat() if isinstance(dt, datetime) else dt.isoformat()
        result.append(FormAnalyticsEntry(
            date=key,
            submissions=submissions_map.get(key, 0),
            failed_webhooks=webhook_map.get(key, 0),
            emails_sent=email_map.get(key, 0),
            unique_ips=ip_map.get(key, 0)
        ))
    return result
