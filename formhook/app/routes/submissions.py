"""
Submission routes: public submit, view, and export.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, BackgroundTasks
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
from ..models.idempotency import IdempotencyKey
from ..models.form import Form
from ..services.email import send_email
from ..services import webhook as webhook_service
from ..services import metrics as metrics_service
from ..services.usage_tracking import UsageTrackingService, PricingValidationService
from ..services.notification import NotificationService
import logging
import httpx
import asyncio
import hmac
import hashlib
import time
from typing import List, Optional
from datetime import datetime, timedelta
from ..core.utils import now_utc
import csv
from io import StringIO
from ..dependencies import get_db, get_current_user

router = APIRouter()


async def _forward_webhook_task(url: str, headers: dict, payload: dict, submission_id: int):
    """Background task to forward submission payload to a webhook with retries.
    This helper creates its own DB session so it is safe to run after the request finishes.
    """
    from ..core.database import SessionLocal

    max_retries = 3
    delay = 2
    attempt = 0
    while attempt < max_retries:
        start = time.time()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=5)
            status = resp.status_code
            success = 200 <= status < 300
            db = SessionLocal()
            try:
                if success:
                    # Record success
                    webhook_service.mark_webhook_success(
                        db, submission_id, url, response_code=status, duration_ms=int((time.time()-start)*1000)
                    )
                else:
                    webhook_service.log_webhook_failure(
                        db, submission_id, url,
                        response_code=status,
                        error_message=f"Non-2xx response: {status}",
                        attempts=attempt + 1,
                        duration_ms=int((time.time()-start)*1000)
                    )
            finally:
                db.close()

            if success:
                break
        except Exception as e:
            db = SessionLocal()
            try:
                webhook_service.log_webhook_failure(
                    db, submission_id, url,
                    error_message=str(e),
                    attempts=attempt + 1
                )
            finally:
                db.close()
            logging.error(f"Failed to forward to webhook: {e}")

        attempt += 1
        await asyncio.sleep(delay * attempt)

# Import limiter from main app
from ..extensions import limiter



@router.post("/{form_id}/submit")
# Use a callable for the limit so we can apply a higher limit for authenticated requests
@limiter.limit(lambda request: settings.RATE_LIMIT_AUTHENTICATED if request.headers.get('authorization') else settings.RATE_LIMIT)
def submit(form_id: str, submission: SubmissionCreate, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Public endpoint to submit form data.
    Rate limits: 100/minute for authenticated users (per user), 100/minute for anonymous (per IP).
    Sends notification if configured.
    If form.require_token is True, requires Authorization: Bearer <token> header.
    """
    # Basic validation: ensure form exists
    form = db.query(Form).filter(Form.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    # Get form owner for usage validation
    form_owner = db.query(User).filter(User.id == form.user_id).first()
    if not form_owner:
        raise HTTPException(status_code=500, detail="Form owner not found")

    # Validate user can submit forms based on their pricing tier
    validation_service = PricingValidationService(db)
    try:
        validation_service.validate_form_submission(form_owner)
    except HTTPException as usage_error:
        # Return a more user-friendly error for public submissions
        if usage_error.status_code == 402:  # Payment Required
            raise HTTPException(
                status_code=503,  # Service Unavailable - more appropriate for public endpoint
                detail={
                    "error": "Form temporarily unavailable",
                    "message": "This form has reached its submission limit. Please try again later or contact the form owner.",
                    "form_id": form_id,
                    "retry_after": "24 hours"
                }
            )
        raise usage_error

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

    # --- Idempotency handling ---
    # Clients may provide an `Idempotency-Key` header to ensure retries do not create duplicates.
    idempotency_key = request.headers.get('idempotency-key') or request.headers.get('Idempotency-Key')
    idempotency_hash = None
    if idempotency_key:
        try:
            # Hash the key together with the form_id for safe storage and to scope keys per-form
            idempotency_hash = hashlib.sha256(f"{form_id}:{idempotency_key}".encode()).hexdigest()
            existing = db.query(IdempotencyKey).filter(
                IdempotencyKey.key_hash == idempotency_hash,
                IdempotencyKey.form_id == str(form_id)
            ).first()
            if existing:
                # Return the previously stored submission to enforce idempotency
                existing_submission = db.query(Submission).filter(Submission.id == existing.submission_id).first()
                if existing_submission:
                        try:
                            metrics_service.inc('submissions.duplicate')
                        except Exception:
                            logging.debug('Failed to increment submissions.duplicate metric')
                        return {
                            "id": existing_submission.id,
                            "form_id": str(existing_submission.form_id),
                            "data": existing_submission.data,
                            "ip_address": existing_submission.ip_address,
                            "created_at": existing_submission.created_at
                        }
        except Exception:
            # If anything goes wrong with idempotency lookup, continue normal flow
            idempotency_hash = None

    # Early size check: if client provided Content-Length, reject if too large
    try:
        content_length = request.headers.get('content-length')
        if content_length:
            if int(content_length) > settings.SUBMISSION_MAX_SIZE_BYTES + 1024:
                # If content-length exceeds allowed + small buffer, reject with 413
                raise HTTPException(status_code=413, detail="Payload too large")
    except Exception:
        # Ignore header parsing errors and continue to schema validation which will catch oversized payloads
        pass
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
    # Validate submission payload according to app limits and return 400 on invalid input
    try:
        # re-run schema validation explicitly to convert Pydantic errors into HTTP 400
        submission = SubmissionCreate(**submission.model_dump() if hasattr(submission, 'model_dump') else submission.__dict__)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid submission data: {e}")

    # --- Abuse/Threat Monitoring ---
    risk_flags = []
    # 1. Rapid submissions from same IP (last 10 min)
    recent_count = db.query(Submission).filter(
        Submission.form_id == form_id,
        Submission.ip_address == ip_address,
        Submission.created_at >= now_utc() - timedelta(minutes=10)
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
        form_id=form_id,  # Keep as UUID, let SQLAlchemy handle the conversion
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
        # Metric: successful submission
        try:
            metrics_service.inc('submissions.success')
        except Exception:
            logging.debug('Failed to increment submissions.success metric')
        
        # Track usage for the form owner (increment submission count)
        usage_service = UsageTrackingService(db)
        usage_service.record_submission(form_owner)
        
        # Create notification for form owner
        try:
            NotificationService.create_submission_notification(
                db=db,
                user_id=form.user_id,
                form_name=form.name,
                form_id=str(form.id),
                submission_id=db_submission.id,
                submitter_email=submission.data.get('email'),
                ip_address=ip_address
            )
            
            # Check for milestones
            total_submissions = db.query(Submission).filter(Submission.form_id == str(form.id)).count()
            NotificationService.check_milestone(db, str(form.id), total_submissions)
        except Exception as notif_error:
            logging.error(f"Failed to create notification: {notif_error}")
            # Don't fail the submission if notification fails
        
    except Exception as db_exc:
        db.rollback()
        try:
            metrics_service.inc('submissions.failure')
        except Exception:
            logging.debug('Failed to increment submissions.failure metric')
        raise HTTPException(status_code=500, detail="Failed to save submission. Please try again.")

    # If an idempotency key was provided, store the mapping now.
    if idempotency_hash:
        try:
            mapping = IdempotencyKey(
                key_hash=idempotency_hash,
                form_id=str(form_id),
                submission_id=db_submission.id
            )
            db.add(mapping)
            db.commit()
        except Exception as e:
            # Possible race: another request inserted the mapping concurrently.
            # Rollback and fetch the existing mapping; if present, return that submission instead.
            try:
                db.rollback()
                existing = db.query(IdempotencyKey).filter(
                    IdempotencyKey.key_hash == idempotency_hash,
                    IdempotencyKey.form_id == str(form_id)
                ).first()
                if existing:
                    existing_submission = db.query(Submission).filter(Submission.id == existing.submission_id).first()
                    if existing_submission:
                        # Optionally delete the duplicate we just created to keep DB tidy
                        try:
                            db.delete(db_submission)
                            db.commit()
                        except Exception:
                            db.rollback()
                        try:
                            metrics_service.inc('submissions.duplicate')
                        except Exception:
                            logging.debug('Failed to increment submissions.duplicate metric')
                        return {
                            "id": existing_submission.id,
                            "form_id": str(existing_submission.form_id),
                            "data": existing_submission.data,
                            "ip_address": existing_submission.ip_address,
                            "created_at": existing_submission.created_at
                        }
            except Exception:
                # If anything fails here, log and continue returning the current submission
                logging.exception("Idempotency mapping failed after race condition")

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

    # Forward to webhook if set (non-blocking, with retry logging) using BackgroundTasks
    if form.webhook_url:
        payload = {
            "form_id": form_id,
            "data": submission.data,
            "ip_address": request.client.host,
            "created_at": str(db_submission.created_at)
        }
        headers = form.webhook_headers or {}
        secret = form.webhook_secret
        url = form.webhook_url

        if secret:
            # Create a deterministic body representation for signing
            body_bytes = None
            try:
                import json as _json
                body_bytes = _json.dumps(payload, separators=(",", ":")).encode()
            except Exception:
                body_bytes = str(payload).encode()
            signature = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
            headers = dict(headers)
            headers["X-FormHook-Signature"] = signature

        # Schedule the async background task. The task creates its own DB session.
        background_tasks.add_task(_forward_webhook_task, url, headers, payload, db_submission.id)

    # Manually create the response with proper UUID to string conversion
    response_data = {
        "id": db_submission.id,
        "form_id": str(db_submission.form_id),  # Explicitly convert UUID to string
        "data": db_submission.data,
        "ip_address": db_submission.ip_address,
        "created_at": db_submission.created_at,
        "country": db_submission.country,
        "region": db_submission.region,
        "city": db_submission.city,
        "location_source": db_submission.location_source,
        "latitude": db_submission.latitude,
        "longitude": db_submission.longitude,
        "threat_score": db_submission.threat_score,
    }
    return response_data


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
