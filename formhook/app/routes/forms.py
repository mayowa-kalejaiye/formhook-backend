import logging
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import EmailStr, ValidationError
from typing import List
from datetime import timedelta
from ..core.utils import now_utc

from ..dependencies import get_db, get_current_user
from ..models.user import User
from ..models.form import Form
from ..models.submission import Submission
from ..models.webhook_delivery import WebhookDelivery
from ..models.idempotency import IdempotencyKey
from ..models.email_log import EmailLog
from ..schemas.form import FormCreate, FormOut, FormWithMetadata, PublicFormOut
from ..schemas.webhook_delivery import WebhookDeliveryLogOut
from ..services.usage_tracking import PricingValidationService
from ..core.security import generate_api_token, hash_api_token
from ..services.cache import cache

router = APIRouter()
logger = logging.getLogger(__name__)

"""
Form management routes.
"""

@router.get("/", response_model=List[FormWithMetadata])
def get_forms(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all forms for the current user with submission counts and metadata. Cached for 60 seconds."""
    # Try to get from cache
    cache_key = f"user_forms:{current_user.id}"
    cached_forms = cache.get(cache_key)
    if cached_forms is not None:
        return cached_forms
    
    # Get all forms for the user
    forms = db.query(Form).filter(Form.user_id == current_user.id).all()
    
    # Build enhanced form list with metadata
    forms_with_metadata = []
    seven_days_ago = now_utc() - timedelta(days=7)
    
    for form in forms:
        # Convert UUID to string for query
        form_id_str = str(form.id)
        
        # Get submission counts
        total_submissions = db.query(Submission).filter(Submission.form_id == form_id_str).count()
        recent_submissions = db.query(Submission).filter(
            Submission.form_id == form_id_str,
            Submission.created_at >= seven_days_ago
        ).count()
        
        # Get last submission timestamp
        last_submission = db.query(Submission).filter(
            Submission.form_id == form_id_str
        ).order_by(Submission.created_at.desc()).first()
        
        # Create enhanced form object
        form_dict = {
            "id": form.id,
            "user_id": form.user_id,
            "name": form.name,
            "description": form.description,
            "webhook_url": form.webhook_url,
            "webhook_headers": form.webhook_headers,
            "webhook_secret": form.webhook_secret,
            "notification_email": form.notification_email,
            "redirect_url": form.redirect_url,
            "success_message": form.success_message,
            "fields": form.fields or [],
            "created_at": form.created_at,
            "require_token": bool(form.require_token),
            "submission_count": total_submissions,
            "recent_submissions": recent_submissions,
            "last_submission_at": last_submission.created_at if last_submission else None,
            "status": "active"  # Default status, can be enhanced later
        }
        
        forms_with_metadata.append(FormWithMetadata(**form_dict))
    
    # Cache the result for 60 seconds
    cache.set(cache_key, forms_with_metadata, ttl_seconds=60)
    
    return forms_with_metadata


@router.post("/", response_model=FormOut)
def create_form(form: FormCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new form for the authenticated user. Validates notification_email and fields."""
    
    # Invalidate user forms cache when creating a new form
    cache.delete(f"user_forms:{current_user.id}")
    
    # Validate user can create forms based on their pricing tier
    validation_service = PricingValidationService(db)
    validation_service.validate_form_creation(current_user)
    
    # Validate notification_email if present
    if form.notification_email:
        try:
            EmailStr.validate(form.notification_email)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Invalid notification_email format.")
    # Validate fields (already validated by Pydantic, but double-check for empty list)
    if not isinstance(form.fields, list):
        raise HTTPException(status_code=400, detail="fields must be a list of field definitions")
    for f in form.fields:
        if not hasattr(f, "name") or not hasattr(f, "label") or not hasattr(f, "type") or not hasattr(f, "required"):
            raise HTTPException(status_code=400, detail="Each field must have name, label, type, and required")
    db_form = Form(
        name=form.name,
        description=form.description,
        webhook_url=str(form.webhook_url) if form.webhook_url else None,
        notification_email=form.notification_email,
        redirect_url=str(form.redirect_url) if form.redirect_url else None,
        success_message=form.success_message,
        fields=[f.dict() for f in form.fields],
        user_id=current_user.id
    )
    try:
        db.add(db_form)
        db.commit()
        db.refresh(db_form)
    except Exception as db_exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create form. Please try again.")
    return db_form


@router.get("/{form_id}", response_model=FormWithMetadata)
def get_form(form_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a form by ID (must belong to current user) with submission counts and metadata."""
    form = db.query(Form).filter(Form.id == form_id, Form.user_id == current_user.id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # Get submission metadata
    seven_days_ago = now_utc() - timedelta(days=7)
    form_id_str = str(form.id)
    
    # Get submission counts
    total_submissions = db.query(Submission).filter(Submission.form_id == form_id_str).count()
    recent_submissions = db.query(Submission).filter(
        Submission.form_id == form_id_str,
        Submission.created_at >= seven_days_ago
    ).count()
    
    # Get last submission timestamp
    last_submission = db.query(Submission).filter(
        Submission.form_id == form_id_str
    ).order_by(Submission.created_at.desc()).first()
    
    # Create enhanced form object
    form_dict = {
        "id": form.id,
        "user_id": form.user_id,
        "name": form.name,
        "description": form.description,
        "webhook_url": form.webhook_url,
        "webhook_headers": form.webhook_headers,
        "webhook_secret": form.webhook_secret,
        "notification_email": form.notification_email,
        "redirect_url": form.redirect_url,
        "success_message": form.success_message,
        "fields": form.fields or [],
        "created_at": form.created_at,
        "require_token": bool(form.require_token),
        "submission_count": total_submissions,
        "recent_submissions": recent_submissions,
        "last_submission_at": last_submission.created_at if last_submission else None,
        "status": "active"  # Default status, can be enhanced later
    }
    
    return FormWithMetadata(**form_dict)

@router.delete("/{form_id}")
def delete_form(form_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete a form by ID (must belong to current user)."""
    form = db.query(Form).filter(Form.id == form_id, Form.user_id == current_user.id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    form_id_str = str(form.id)
    submission_ids_subq = db.query(Submission.id).filter(Submission.form_id == form_id_str).subquery()

    try:
        # Remove dependent records that reference this form's submissions
        db.query(WebhookDelivery).filter(WebhookDelivery.submission_id.in_(submission_ids_subq)).delete(synchronize_session=False)
        db.query(IdempotencyKey).filter(IdempotencyKey.submission_id.in_(submission_ids_subq)).delete(synchronize_session=False)
        db.query(EmailLog).filter(EmailLog.form_id == form_id_str).delete(synchronize_session=False)
        db.query(Submission).filter(Submission.form_id == form_id_str).delete(synchronize_session=False)

        db.delete(form)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to delete form %s", form_id_str)
        raise HTTPException(status_code=500, detail="Failed to delete form. Please try again.") from exc
    
    # Invalidate cache
    cache.delete(f"user_forms:{current_user.id}")
    cache.delete(f"form:{form_id}")
    
    return {"detail": "Form deleted"}

# --- API Token Management Endpoints ---

@router.post("/{form_id}/generate-token", status_code=200, tags=["Forms"], summary="Generate API token for a form", description="Generate a unique API token for a form. Only the form owner can call this. The token is returned once and stored hashed. Overwrites any existing token.")
def generate_form_token(form_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    form = db.query(Form).filter(Form.id == form_id, Form.user_id == current_user.id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found or not authorized")
    token = generate_api_token()
    form.api_token = hash_api_token(token)
    form.require_token = 1
    db.commit()
    return {"token": token, "message": "Store this token securely. It will not be shown again."}

@router.delete("/{form_id}/revoke-token", status_code=204, tags=["Forms"], summary="Revoke API token for a form", description="Revoke the API token for a form. Only the form owner can call this. After revocation, submissions will not require a token unless a new one is generated.")
def revoke_form_token(form_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    form = db.query(Form).filter(Form.id == form_id, Form.user_id == current_user.id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found or not authorized")
    form.api_token = None
    form.require_token = 0
    db.commit()
    return Response(status_code=204)

@router.get("/{form_id}/webhook-deliveries", response_model=List[WebhookDeliveryLogOut])
def get_webhook_deliveries(form_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get webhook delivery logs for a form (auth required, must own form)."""
    form = db.query(Form).filter(Form.id == form_id, Form.user_id == current_user.id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    logs = db.query(WebhookDelivery).filter(WebhookDelivery.form_id == str(form_id)).order_by(WebhookDelivery.last_attempt_at.desc()).all()
    return logs


# Public endpoint - no authentication required
@router.get("/public/{form_id}", response_model=PublicFormOut)
def get_public_form(form_id: str, db: Session = Depends(get_db)):
    """Get form structure for public submissions (no auth required).
    
    Returns only the form structure needed for rendering the form publicly:
    - Form ID, name, description
    - Field definitions (name, label, type, required)
    
    Does not include sensitive information like webhook URLs, API tokens, etc.
    """
    form = db.query(Form).filter(Form.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    return PublicFormOut(
        id=form.id,
        name=form.name,
        description=form.description,
        fields=form.fields or []
    )
