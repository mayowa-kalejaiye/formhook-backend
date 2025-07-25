"""
Service for forwarding submissions to a webhook URL and retrying failed deliveries.
"""
import requests
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.webhook_delivery import WebhookDelivery
from ..models.submission import Submission
from ..core.database import SessionLocal
import logging

# Exponential backoff schedule (in seconds)
RETRY_SCHEDULE = [5, 30, 120, 600, 1800]  # 5s, 30s, 2m, 10m, 30m
MAX_ATTEMPTS = len(RETRY_SCHEDULE)

def log_webhook_failure(db: Session, submission_id: int, webhook_url: str, response_code: int = None, error_message: str = None, attempts: int = 1):
    now = datetime.utcnow()
    # Calculate next_retry_at with jitter
    if attempts <= MAX_ATTEMPTS:
        base_delay = RETRY_SCHEDULE[attempts-1]
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
        error_message=error_message
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery

def update_webhook_delivery(db: Session, delivery: WebhookDelivery, status: str, response_code: int = None, error_message: str = None):
    now = datetime.utcnow()
    delivery.status = status
    delivery.last_attempt_at = now
    delivery.response_code = response_code
    delivery.error_message = error_message
    if status == "PENDING" and delivery.attempts < MAX_ATTEMPTS:
        base_delay = RETRY_SCHEDULE[delivery.attempts]
        jitter = random.uniform(0, base_delay * 0.2)
        delivery.next_retry_at = now + timedelta(seconds=base_delay + jitter)
    else:
        delivery.next_retry_at = None
    db.commit()
    db.refresh(delivery)
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
    now = datetime.utcnow()
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
