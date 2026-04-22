"""
Password reset service for FormHook.
"""
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.security import hash_password
from ..core.utils import now_utc
from ..models.password_reset import PasswordReset
from ..models.user import User
from ..services.email import send_email


def create_password_reset_token(db: Session, user_id: int) -> str:
    """Create a fresh password reset token and invalidate any unused tokens for the user."""
    existing_tokens = db.query(PasswordReset).filter(
        PasswordReset.user_id == user_id,
        PasswordReset.is_used == False,  # noqa: E712
    ).all()
    for token in existing_tokens:
        token.is_used = True

    reset_token = PasswordReset(user_id=user_id)
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    return reset_token.token


def send_password_reset_email(db: Session, user: User) -> bool:
    """Send a password reset email to the user."""
    token = create_password_reset_token(db, user.id)
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    subject = "Reset your FormHook password"
    html_content = f"""
    <div style="font-family:Arial,Helvetica,sans-serif;line-height:1.5;color:#111">
        <h2 style="margin-bottom:16px">Reset your password</h2>
        <p>We received a request to reset your FormHook password. Click the button below to continue:</p>
        <p style="margin:24px 0">
            <a href="{reset_url}"
               style="display:inline-block;background:#111;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:600">
                Reset password
            </a>
        </p>
        <p style="margin-bottom:16px">If the button doesn't work, copy and paste this link into your browser:<br/>
            <a href="{reset_url}" style="color:#0070f3">{reset_url}</a>
        </p>
        <p style="font-size:13px;color:#555">This link expires in 1 hour. If you did not request a reset, you can ignore this email.</p>
    </div>
    """

    try:
        send_email(to_email=user.email, subject=subject, html_content=html_content)
        return True
    except Exception as exc:
        print(f"Error sending password reset email: {exc}")
        return False


def reset_password(db: Session, token: str, new_password: str) -> bool:
    """Validate a token and update the user's password."""
    try:
        reset_record = db.query(PasswordReset).filter(
            PasswordReset.token == token,
            PasswordReset.is_used == False,  # noqa: E712
            PasswordReset.expires_at > now_utc(),
        ).first()

        if not reset_record:
            return False

        user = db.query(User).filter(User.id == reset_record.user_id).first()
        if not user:
            return False

        user.password_hash = hash_password(new_password)
        user.token_version = int(getattr(user, "token_version", 0) or 0) + 1
        reset_record.is_used = True

        # Invalidate any other outstanding reset links for this user.
        db.query(PasswordReset).filter(
            PasswordReset.user_id == user.id,
            PasswordReset.is_used == False,  # noqa: E712
        ).update({"is_used": True})

        db.commit()
        return True
    except Exception as exc:
        print(f"Error resetting password: {exc}")
        db.rollback()
        return False
