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
import httpx
import asyncio
import hmac
import hashlib
import time
from typing import List, Optional
from datetime import datetime, timedelta
import csv
from io import StringIO
from ..dependencies import get_db, get_current_user

router = APIRouter()

# Import limiter from main app
from ..extensions import limiter



@router.post("/{form_id}/submit", response_model=SubmissionOut)
@limiter.limit("5/minute")  # Custom rate limit: 5 submissions per minute per IP
def submit(form_id: str, submission: SubmissionCreate, request: Request, db: Session = Depends(get_db)):
    """Public endpoint to submit form data. Limited to 5 submissions per minute per IP. Sends notification if set.
    If form.require_token is True, requires Authorization: Bearer <token> header matching the stored token.
    """
    form = db.query(Form).filter(Form.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    # --- API Token validation ---
    if getattr(form, "require_token", 0):
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            log_failed_token_attempt(db, form_id, request.client.host, reason="Missing or invalid Authorization header")
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
        token = auth_header.split(" ", 1)[1].strip()
        from ..core.security import verify_password
        if not form.api_token or not verify_password(token, form.api_token):
            log_failed_token_attempt(db, form_id, request.client.host, reason="Invalid token")
            raise HTTPException(status_code=401, detail="Invalid API token")

    from ..services.geo import extract_client_ip, get_geolocation
    ip_address = extract_client_ip(request)
    geo_data = None
    country = region = city = location_source = latitude = longitude = None
    if getattr(form, "track_location", 0):
        geo_data = get_geolocation(ip_address)
        if geo_data:
            country = geo_data.get('country')
            region = geo_data.get('region')
            city = geo_data.get('city')
            location_source = geo_data.get('location_source')
            latitude = geo_data.get('latitude')
            longitude = geo_data.get('longitude')
    # --- Abuse/Threat Monitoring ---
    risk_flags = []
    # 1. Rapid submissions from same IP (last 10 min)
    recent_count = db.query(Submission).filter(
        Submission.form_id == form_id,
        Submission.ip_address == ip_address,
        Submission.created_at >= datetime.utcnow() - timedelta(minutes=10)
    ).count()
    if recent_count > 5:
        risk_flags.append("rapid_submissions")
    # 2. Datacenter IP detection (simple: org contains 'Google', 'Amazon', 'Microsoft', etc.)
    if geo_data and geo_data.get('org'):
        org = geo_data['org'].lower()
        if any(dc in org for dc in ['google', 'amazon', 'microsoft', 'digitalocean', 'ovh', 'linode', 'hetzner']):
            risk_flags.append("datacenter_ip")
    # 3. Country mismatch (if you want to compare to user profile or previous submissions)
    # Example: if form.user_id has a profile country, compare here
    # 4. Add risk flags to webhook logs (extend as needed)
    db_submission = Submission(
        form_id=str(form_id),  # Convert to string explicitly
        data=submission.data,
        ip_address=ip_address,
        country=country,
        region=region,
        city=city,
        location_source=location_source,
        latitude=latitude,
        longitude=longitude,
        threat_score=len(risk_flags) if risk_flags else None
    )
    try:
        db.add(db_submission)
        db.commit()
        db.refresh(db_submission)
    except Exception as db_exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save submission. Please try again.")

    # Send notification email if set
    if form.notification_email:
        try:
            response = send_email(
                to_email=form.notification_email,
                subject=f"New submission for form '{form.name}'",
                html_content=f"<p>You have a new submission for your form <b>{form.name}</b>.</p><pre>{submission.data}</pre>"
            )
            # Log the email event
            if hasattr(response, "log_email"):
                response.log_email(db=db, form_id=str(form.id), submission_id=db_submission.id)
        except Exception as e:
            logging.error(f"Failed to send notification email: {e}")
            raise HTTPException(status_code=500, detail="Failed to send notification email.")

    # Forward to webhook if set (non-blocking, with retry logging, advanced logic)
    if form.webhook_url:
        def run_webhook_forwarding():
            async def forward_with_retries():
                max_retries = 3
                delay = 2
                attempt = 0
                payload = {
                    "form_id": form_id,
                    "data": submission.data,
                    "ip_address": request.client.host,
                    "created_at": str(db_submission.created_at)
                }
                headers = form.webhook_headers or {}
                # HMAC signature if secret is set
                if form.webhook_secret:
                    body = httpx.dumps(payload).encode() if hasattr(httpx, 'dumps') else str(payload).encode()
                    signature = hmac.new(form.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
                    headers = dict(headers)  # ensure mutable
                    headers["X-FormHook-Signature"] = signature
                url = form.webhook_url
                while attempt < max_retries:
                    start = time.time()
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.post(url, json=payload, headers=headers, timeout=5)
                        duration = int((time.time() - start) * 1000)
                        success = 200 <= resp.status_code < 300
                        webhook_service.log_webhook_failure(
                            db, db_submission.id, url,
                            response_code=resp.status_code,
                            error_message=None if success else f"Non-2xx response: {resp.status_code}",
                            attempts=attempt+1
                        )
                        # Optionally, update log with headers, response_body, retry_count, duration_ms
                        # (Extend webhook_service as needed)
                        if success:
                            break
                    except Exception as e:
                        duration = int((time.time() - start) * 1000)
                        webhook_service.log_webhook_failure(
                            db, db_submission.id, url,
                            error_message=str(e),
                            attempts=attempt+1
                        )
                        logging.error(f"Failed to forward to webhook: {e}")
                    attempt += 1
                    await asyncio.sleep(delay * attempt)  # Exponential backoff
            asyncio.run(forward_with_retries())
        threading.Thread(target=run_webhook_forwarding, daemon=True).start()

    return db_submission


# --- Helper: Log failed token attempts ---
def log_failed_token_attempt(db, form_id, ip, reason):
    from datetime import datetime
    logging.warning(f"Failed token attempt: form_id={form_id}, ip={ip}, reason={reason}")
    # Optionally, store in a DB table for audit (not implemented here)
    # Example: db.add(FailedTokenAttempt(...)); db.commit()
# Admin endpoint to manually retry pending webhooks
from fastapi import APIRouter
from fastapi import BackgroundTasks

@router.post("/admin/retry-webhooks")
def retry_webhooks(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually retry all pending webhook deliveries (admin only)."""
    background_tasks.add_task(webhook_service.retry_pending_webhooks, db)
    return {"detail": "Webhook retry task started."}

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
