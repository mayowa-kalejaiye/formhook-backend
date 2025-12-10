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
    <div style="font-family:Arial,Helvetica,sans-serif;line-height:1.5;color:#111">
        <h2 style="margin-bottom:16px">Confirm your email address</h2>
        <p>Thanks for signing up for FormHook. Click the button below to verify your email and finish setting up your workspace:</p>
        <p style="margin:24px 0">
            <a href="{verification_url}"
               style="display:inline-block;background:#111;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:600">
                Verify email
            </a>
        </p>
        <p style="margin-bottom:16px">If the button doesn't work, copy and paste this link into your browser:<br/>
            <a href="{verification_url}" style="color:#0070f3">{verification_url}</a>
        </p>
        <p style="font-size:13px;color:#555">This link expires in 24 hours. If you didn't create a FormHook account, you can safely ignore this message.</p>
    </div>
    """
    
    # Send email using your existing email service
    try:
        send_email(to_email=user.email, subject=subject, html_content=content)
        return True
    except Exception as e:
        print(f"Error sending verification email: {e}")
        return False
