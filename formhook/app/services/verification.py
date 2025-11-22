"""
Service for email verification functionality.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..core.utils import now_utc
import uuid
import os

from ..models.user import User
from ..models.verification import EmailVerification
from ..services.email import send_email
from ..core.config import settings

def create_verification_token(db: Session, user_id: int) -> str:
    """
    Create a new verification token for a user, invalidating any existing ones.
    """
    # Invalidate any existing tokens
    existing_tokens = db.query(EmailVerification).filter(
        EmailVerification.user_id == user_id,
        EmailVerification.is_used == False
    ).all()
    for token in existing_tokens:
        token.is_used = True
    
    # Create new token
    verification = EmailVerification(user_id=user_id)
    db.add(verification)
    db.commit()
    db.refresh(verification)
    
    return verification.token

def verify_email(db: Session, token: str) -> bool:
    """
    Verify a user's email using a token.
    Returns True if successful, False otherwise.
    """
    try:
        verification = db.query(EmailVerification).filter(
            EmailVerification.token == token,
            EmailVerification.is_used == False,
            EmailVerification.expires_at > now_utc()
        ).first()
        
        if not verification:
            return False
        
        # Mark token as used
        verification.is_used = True
        
        # Mark user as verified
        user = db.query(User).filter(User.id == verification.user_id).first()
        if user:
            user.is_verified = True
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error verifying email: {e}")
        db.rollback()
        return False

def send_verification_email(db: Session, user: User, base_url: str = None) -> bool:
    """
    Send a verification email to a user.
    Returns True if email was sent successfully, False otherwise.
    """
    token = create_verification_token(db, user.id)
    
    # Use the frontend URL from settings for verification links
    frontend_url = settings.FRONTEND_URL
    verification_url = f"{frontend_url}/verify-email?token={token}"
    
    # Email content
    subject = "Verify your FormHook account"
    content = f"""
    <h1>Verify your email address</h1>
    <p>Thank you for signing up for FormHook! Please verify your email address by clicking the link below:</p>
    <p><a href="{verification_url}">Verify Email</a></p>
    <p>This link will expire in 24 hours.</p>
    <p>If you didn't create an account, you can ignore this email.</p>
    """
    
    # Send email using your existing email service
    try:
        send_email(to_email=user.email, subject=subject, html_content=content)
        return True
    except Exception as e:
        print(f"Error sending verification email: {e}")
        return False
