"""
Service for forwarding submissions to a webhook URL and retrying failed deliveries.
"""
import requests
import random
from datetime import timedelta
from ..core.utils import now_utc
from sqlalchemy.orm import Session
from ..models.webhook_delivery import WebhookDelivery
from ..models.submission import Submission
from ..core.database import SessionLocal
import logging

# Exponential backoff schedule (in seconds)
RETRY_SCHEDULE = [5, 30, 120, 600, 1800]  # 5s, 30s, 2m, 10m, 30m
MAX_ATTEMPTS = len(RETRY_SCHEDULE)

def log_webhook_failure(
    db: Session,
    submission_id: int,
    webhook_url: str,
    response_code: int = None,
    error_message: str = None,
    attempts: int = 1,
    response_body: str | None = None,
    headers_sent: dict | None = None,
    duration_ms: int | None = None,
):
    """Create a WebhookDelivery record (or update) recording a failed or attempted delivery.
    Stores response body, headers sent, duration, and schedules next retry using exponential backoff.
    """
    now = now_utc()
    # Calculate next_retry_at with jitter if still retrying
    if attempts <= MAX_ATTEMPTS:
        base_delay = RETRY_SCHEDULE[min(attempts - 1, len(RETRY_SCHEDULE) - 1)]
        jitter = random.uniform(0, base_delay * 0.2)
        next_retry = now + timedelta(seconds=base_delay + jitter)
    else:
        next_retry = None
    status = "PENDING" if attempts <= MAX_ATTEMPTS else "FAILED"

    delivery = WebhookDelivery(
        submission_id=submission_id,
        webhook_url=webhook_url,
        status=status,
        attempts=attempts,
        last_attempt_at=now,
        next_retry_at=next_retry,
        response_code=response_code,
        error_message=error_message,
        response_body=(response_body[:2000] if response_body else None),
        headers_sent=headers_sent,
        duration_ms=duration_ms,
        retry_count=attempts,
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    # Metric: webhook failure/attempt
    try:
        from . import metrics as metrics_service
        metrics_service.inc('webhook.failure')
    except Exception:
        pass
    return delivery

def update_webhook_delivery(
    db: Session,
    delivery: WebhookDelivery,
    status: str,
    response_code: int = None,
    error_message: str = None,
    response_body: str | None = None,
    headers_sent: dict | None = None,
    duration_ms: int | None = None,
):
    now = now_utc()
    delivery.status = status
    delivery.last_attempt_at = now
    delivery.response_code = response_code
    delivery.error_message = error_message
    if response_body:
        delivery.response_body = response_body[:2000]
    if headers_sent:
        delivery.headers_sent = headers_sent
    if duration_ms is not None:
        delivery.duration_ms = duration_ms

    # Increment attempts and schedule next retry if applicable
    delivery.attempts = (delivery.attempts or 0) + 1
    delivery.retry_count = delivery.attempts
    if status == "PENDING" and delivery.attempts < MAX_ATTEMPTS:
        base_delay = RETRY_SCHEDULE[min(delivery.attempts - 1, len(RETRY_SCHEDULE) - 1)]
        jitter = random.uniform(0, base_delay * 0.2)
        delivery.next_retry_at = now + timedelta(seconds=base_delay + jitter)
    else:
        delivery.next_retry_at = None
    db.commit()
    db.refresh(delivery)
    # Metric: webhook retry
    try:
        from . import metrics as metrics_service
        metrics_service.inc('webhook.retry')
    except Exception:
        pass
    return delivery


def mark_webhook_success(db: Session, submission_id: int, webhook_url: str, response_code: int = None, response_body: str | None = None, headers_sent: dict | None = None, duration_ms: int | None = None):
    """Record a successful webhook delivery."""
    now = now_utc()
    delivery = WebhookDelivery(
        submission_id=submission_id,
        webhook_url=webhook_url,
        status="SUCCESS",
        attempts=1,
        last_attempt_at=now,
        next_retry_at=None,
        response_code=response_code,
        response_body=(response_body[:2000] if response_body else None),
        headers_sent=headers_sent,
        duration_ms=duration_ms,
        retry_count=1,
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    try:
        from . import metrics as metrics_service
        metrics_service.inc('webhook.success')
    except Exception:
        pass
    return delivery

def forward_webhook(submission: Submission, webhook_url: str, db: Session, delivery: WebhookDelivery = None):
    """
    Try to POST submission data to webhook_url. If fails, log or update delivery for retry.
    """
    try:
        resp = requests.post(
            webhook_url,
            json={
                "form_id": submission.form_id,
                "data": submission.data,
                "ip_address": submission.ip_address,
                "created_at": str(submission.created_at)
            },
            timeout=5
        )
        if 200 <= resp.status_code < 300:
            if delivery:
                update_webhook_delivery(db, delivery, status="SUCCESS", response_code=resp.status_code)
            return True
        else:
            msg = f"Non-2xx response: {resp.status_code}"
            if delivery:
                update_webhook_delivery(db, delivery, status="PENDING", response_code=resp.status_code, error_message=msg)
            else:
                log_webhook_failure(db, submission.id, webhook_url, response_code=resp.status_code, error_message=msg)
            return False
    except Exception as e:
        msg = str(e)
        if delivery:
            update_webhook_delivery(db, delivery, status="PENDING", error_message=msg)
        else:
            log_webhook_failure(db, submission.id, webhook_url, error_message=msg)
        logging.error(f"Webhook delivery failed: {msg}")
        return False

def retry_pending_webhooks(db: Session):
    """
    Retry all pending webhook deliveries whose next_retry_at <= now().
    """
    now = now_utc()
    pending = db.query(WebhookDelivery).filter(
        WebhookDelivery.status == "PENDING",
        WebhookDelivery.next_retry_at != None,
        WebhookDelivery.next_retry_at <= now,
        WebhookDelivery.attempts < MAX_ATTEMPTS
    ).all()
    for delivery in pending:
        submission = db.query(Submission).filter(Submission.id == delivery.submission_id).first()
        if not submission:
            update_webhook_delivery(db, delivery, status="FAILED", error_message="Submission not found")
            continue
        delivery.attempts += 1
        db.commit()
        forward_webhook(submission, delivery.webhook_url, db, delivery=delivery)
