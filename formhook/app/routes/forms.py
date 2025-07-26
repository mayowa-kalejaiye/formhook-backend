"""
Form management routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from fastapi.security import OAuth2PasswordBearer
from ..models.user import User
from sqlalchemy.orm import Session
from ..schemas.form import FormCreate, FormOut
from pydantic import EmailStr, ValidationError
from ..models.form import Form
from typing import List
from ..dependencies import get_db, get_current_user


router = APIRouter()


@router.get("/", response_model=List[FormOut])
def get_forms(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all forms for the current user."""
    return db.query(Form).filter(Form.user_id == current_user.id).all()

@router.post("/", response_model=FormOut)
def create_form(form: FormCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new form for the authenticated user. Validates notification_email if provided."""
    # Validate notification_email if present
    if form.notification_email:
        try:
            EmailStr.validate(form.notification_email)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Invalid notification_email format.")
    db_form = Form(**form.dict(), user_id=current_user.id)
    db.add(db_form)
    db.commit()
    db.refresh(db_form)
    return db_form

@router.get("/{form_id}", response_model=FormOut)
def get_form(form_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a form by ID (must belong to current user)."""
    form = db.query(Form).filter(Form.id == form_id, Form.user_id == current_user.id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form

@router.delete("/{form_id}")
def delete_form(form_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete a form by ID (must belong to current user)."""
    form = db.query(Form).filter(Form.id == form_id, Form.user_id == current_user.id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    db.delete(form)
    db.commit()
    return {"detail": "Form deleted"}
