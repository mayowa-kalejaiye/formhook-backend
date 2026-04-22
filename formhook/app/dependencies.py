"""
Shared dependencies for FastAPI routes.
"""
import logging
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi import Request
from sqlalchemy.orm import Session
from .core.security import decode_access_token
from .models.user import User
from .core.database import SessionLocal
from .core.config import settings

# Update tokenUrl to match our new standard OAuth2 endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
logger = logging.getLogger(__name__)


def get_token_from_request(request: Request) -> str:
    """Extract access token from HttpOnly cookie `access_token`, falling back to Authorization header.
    Raises HTTPException if no token found.
    """
    # 1) Try cookie
    token = request.cookies.get("access_token")
    if token:
        return token

    # 2) Fallback to Authorization header (Bearer)
    auth: str = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(get_token_from_request), db: Session = Depends(get_db)):
    try:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        payload = decode_access_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token or token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user identifier",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user = db.query(User).filter(User.id == int(payload["sub"])).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_version = int(payload.get("token_version", 0) or 0)
        current_version = int(getattr(user, "token_version", 0) or 0)
        if token_version != current_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please verify your email before accessing this resource."
            )
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Authentication error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during authentication: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require an authenticated admin user."""
    if not bool(getattr(current_user, "is_admin", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
