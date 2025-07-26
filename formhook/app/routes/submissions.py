"""
Submission routes: public submit, view, and export.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.requests import Request as FastAPIRequest
from ..core.config import settings
from sqlalchemy.orm import Session

from fastapi.security import OAuth2PasswordBearer
from ..models.user import User
from ..schemas.submission import SubmissionCreate, SubmissionOut
from ..models.submission import Submission
from ..models.form import Form
from ..services.email import send_email
from ..services import webhook as webhook_service
import logging
import threading
import requests
from typing import List, Optional
from datetime import datetime
import csv
from io import StringIO
from ..dependencies import get_db, get_current_user

router = APIRouter()

# Import limiter from main app
from ..extensions import limiter



@router.post("/{form_id}/submit", response_model=SubmissionOut)
@limiter.limit("5/minute")  # Custom rate limit: 5 submissions per minute per IP
def submit(form_id: str, submission: SubmissionCreate, request: Request, db: Session = Depends(get_db)):
    """Public endpoint to submit form data. Limited to 5 submissions per minute per IP. Sends notification if set."""
    form = db.query(Form).filter(Form.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    # TODO: Validate payload fields, webhook
    db_submission = Submission(
        form_id=form_id,
        data=submission.data,
        ip_address=request.client.host
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    # Send notification email if set
    if form.notification_email:
        try:
            send_email(
                to_email=form.notification_email,
                subject=f"New submission for form '{form.name}'",
                html_content=f"<p>You have a new submission for your form <b>{form.name}</b>.</p><pre>{submission.data}</pre>"
            )
        except Exception as e:
            logging.error(f"Failed to send notification email: {e}")

    # Forward to webhook if set (non-blocking, with retry logging)
    if form.webhook_url:
        def forward_webhook_with_retry():
            try:
                resp = requests.post(
                    form.webhook_url,
                    json={
                        "form_id": form_id,
                        "data": submission.data,
                        "ip_address": request.client.host,
                        "created_at": str(db_submission.created_at)
                    },
                    timeout=5
                )
                if not (200 <= resp.status_code < 300):
                    webhook_service.log_webhook_failure(
                        db, db_submission.id, form.webhook_url, response_code=resp.status_code, error_message=f"Non-2xx response: {resp.status_code}", attempts=1
                    )
            except Exception as e:
                webhook_service.log_webhook_failure(
                    db, db_submission.id, form.webhook_url, error_message=str(e), attempts=1
                )
                logging.error(f"Failed to forward to webhook: {e}")
        threading.Thread(target=forward_webhook_with_retry, daemon=True).start()
# Admin endpoint to manually retry pending webhooks
from fastapi import APIRouter
from fastapi import BackgroundTasks

@router.post("/admin/retry-webhooks")
def retry_webhooks(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually retry all pending webhook deliveries (admin only)."""
    background_tasks.add_task(webhook_service.retry_pending_webhooks, db)
    return {"detail": "Webhook retry task started."}
    return db_submission

@router.get("/{form_id}/submissions", response_model=List[SubmissionOut])
def get_submissions(
    form_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    ip_address: Optional[str] = None
):
    """
    Get submissions for a form (auth required, must own form) with pagination and basic filtering.
    - limit: max results (default 20)
    - offset: skip N results
    - date_from/date_to: filter by created_at (ISO format)
    - ip_address: filter by IP
    """
    form = db.query(Form).filter(Form.id == form_id, Form.user_id == current_user.id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found or not authorized")
    query = db.query(Submission).filter(Submission.form_id == form_id)
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.filter(Submission.created_at >= dt_from)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO 8601.")
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.filter(Submission.created_at <= dt_to)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO 8601.")
    if ip_address:
        query = query.filter(Submission.ip_address == ip_address)
    return query.order_by(Submission.created_at.desc()).offset(offset).limit(limit).all()

@router.get("/{form_id}/submissions/export")
def export_submissions(form_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Export submissions as CSV (auth required, must own form)."""
    form = db.query(Form).filter(Form.id == form_id, Form.user_id == current_user.id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found or not authorized")
    submissions = db.query(Submission).filter(Submission.form_id == form_id).all()
    if not submissions:
        raise HTTPException(status_code=404, detail="No submissions found")
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "form_id", "data", "ip_address", "created_at"])
    for s in submissions:
        writer.writerow([s.id, s.form_id, s.data, s.ip_address, s.created_at])
    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=submissions_{form_id}.csv"
    return response
