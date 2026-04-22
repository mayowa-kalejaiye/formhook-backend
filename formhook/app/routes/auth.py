"""
Auth routes: signup, login, and email verification.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..schemas.user import UserOut
from ..models.user import User
from ..core.database import SessionLocal
from ..core.security import hash_password, verify_password, create_access_token
from ..models.auth_security_counter import AuthSecurityCounter
from ..schemas.verification import EmailVerificationRequest, EmailVerificationResponse, TokenVerification
from ..services.verification import verify_email, send_verification_email
from ..services.password_reset import send_password_reset_email, reset_password
from ..extensions import limiter
from pydantic import EmailStr, BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from ..core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def log_failed_auth_attempt(db: Session, request: Request, endpoint: str, email: str) -> None:
    client_ip = request.client.host if request.client else "unknown"
    attempt_count = None

    try:
        counter = db.query(AuthSecurityCounter).filter(
            AuthSecurityCounter.endpoint == endpoint,
            AuthSecurityCounter.email == email,
            AuthSecurityCounter.ip_address == client_ip,
        ).first()

        if counter is None:
            counter = AuthSecurityCounter(
                endpoint=endpoint,
                email=email,
                ip_address=client_ip,
                attempts=1,
            )
            db.add(counter)
            attempt_count = 1
        else:
            counter.attempts = int(counter.attempts or 0) + 1
            attempt_count = counter.attempts

        db.commit()
    except Exception:
        # Fail open for auth flow if telemetry storage is unavailable.
        db.rollback()
        logger.warning(
            "Failed to persist auth security counter endpoint=%s email=%s ip=%s",
            endpoint,
            email,
            client_ip,
        )

    # Keep warnings meaningful by surfacing notable thresholds.
    if attempt_count is None or attempt_count in {1, 5, 10} or attempt_count % 25 == 0:
        logger.warning(
            "Failed auth attempt endpoint=%s email=%s ip=%s attempts=%s",
            endpoint,
            email,
            client_ip,
            attempt_count,
        )
    else:
        logger.debug(
            "Failed auth attempt endpoint=%s email=%s ip=%s attempts=%s",
            endpoint,
            email,
            client_ip,
            attempt_count,
        )


def normalize_email(value: str) -> str:
    return value.strip().lower()


def build_auth_token_payload(user: User) -> dict:
    return {
        "sub": str(user.id),
        "email": user.email,
        "token_version": int(getattr(user, "token_version", 0) or 0),
    }

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", response_model=UserOut)
@limiter.limit("5/minute")
async def signup(
    request: Request,
    email: str = Form(None),
    password: str = Form(None),
    db: Session = Depends(get_db)
):
    """Register a new user and send verification email. Accepts both form data and JSON."""
    try:
        logger.debug("Signup request received content_type=%s", request.headers.get("content-type", "unknown"))
        
        # Try to get data from form first
        if email is not None and password is not None:
            # Form data was provided
            user_email = email
            user_password = password
            logger.debug("Signup using form payload")
        else:
            # Try to parse JSON body
            try:
                body = await request.json()
                user_email = body.get("email")
                user_password = body.get("password")
                
                if not user_email or not user_password:
                    raise HTTPException(
                        status_code=422,
                        detail="Missing required fields: email and password"
                    )
            except HTTPException:
                raise
            except Exception:
                # If we can't parse JSON and don't have form data, raise error
                logger.warning("Signup request payload parsing failed")
                raise HTTPException(
                    status_code=422,
                    detail="Invalid request format. Please provide email and password."
                )
        
        if not user_email or not user_password:
            raise HTTPException(
                status_code=422,
                detail="Missing required fields: email and password"
            )

        # Check if email already exists
        user_email = normalize_email(user_email)

        existing_user = db.query(User).filter(func.lower(User.email) == user_email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email address already registered. Please use a different email or log in.")
        
        # Create user on the active free plan.
        db_user = User(
            email=user_email,
            password_hash=hash_password(user_password),
            subscription_status="active",
            trial_ends_at=None
        )
        if not settings.REQUIRE_EMAIL_VERIFICATION:
            db_user.is_verified = True
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Send verification email
        if settings.REQUIRE_EMAIL_VERIFICATION:
            try:
                send_verification_email(db, db_user)
            except Exception as e:
                # Log the error but don't fail the signup
                logger.warning("Error sending verification email for user_id=%s: %s", db_user.id, e)
        
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        # Log any other errors
        logger.exception("Signup error")
        db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed. Please try again later.")


# Pydantic model for login request
class LoginRequest(BaseModel):
    email: str  # Changed to match the React form field name
    password: str

@router.post("/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    email: str = Form(None), 
    password: str = Form(None),
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT. Accepts both form data and JSON."""
    try:
        logger.debug("Login request received content_type=%s", request.headers.get("content-type", "unknown"))
        
        # Try to get data from form first
        if email is not None and password is not None:
            # Form data was provided
            user_email = email
            user_password = password
            logger.debug("Login using form payload")
        else:
            # Try to parse JSON body
            try:
                body = await request.json()
                user_email = body.get("email")
                user_password = body.get("password")
                
                if not user_email or not user_password:
                    raise HTTPException(
                        status_code=422,
                        detail="Missing required fields: email and password"
                    )
            except HTTPException:
                raise
            except Exception:
                # If we can't parse JSON and don't have form data, raise error
                logger.warning("Login request payload parsing failed")
                raise HTTPException(
                    status_code=422,
                    detail="Invalid request format. Please provide email and password."
                )
        
        user_email = normalize_email(user_email)

        if not user_email or not user_password:
            raise HTTPException(
                status_code=422,
                detail="Missing required fields: email and password"
            )

        # Find the user
        user = db.query(User).filter(func.lower(User.email) == user_email).first()
        if not user or not verify_password(user_password, user.password_hash):
            log_failed_auth_attempt(db, request, "/auth/login", user_email)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        
        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified. Please check your inbox for a verification link."
            )
        
        token = create_access_token(build_auth_token_payload(user))
        # Prepare user payload
        user_data = {"id": user.id, "email": user.email, "is_verified": user.is_verified}
        # Set HttpOnly cookie for session-based auth (keeps compatibility by returning token in body)
        secure_cookie = settings.FRONTEND_URL.startswith("https")
        resp = JSONResponse({"access_token": token, "token_type": "bearer", "user": user_data})
        resp.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=secure_cookie,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        return resp
    except HTTPException:
        raise
    except Exception:
        logger.exception("Login error")
        raise HTTPException(status_code=500, detail=f"Login failed. Please try again later.")

# Email login model
class EmailLoginRequest(BaseModel):
    email: str  # Changed from EmailStr to str for more flexibility
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str

@router.post("/email-login")
@limiter.limit("10/minute")
def email_login(request: Request, payload: EmailLoginRequest, db: Session = Depends(get_db)):
    """Alternative login endpoint accepting 'email' instead of 'username'."""
    try:
        normalized_email = normalize_email(payload.email)
        user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
        if not user or not verify_password(payload.password, user.password_hash):
            log_failed_auth_attempt(db, request, "/auth/email-login", normalized_email)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        
        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified. Please check your inbox for a verification link."
            )
        
        token = create_access_token(build_auth_token_payload(user))
        user_data = {"id": user.id, "email": user.email, "is_verified": user.is_verified}
        secure_cookie = settings.FRONTEND_URL.startswith("https")
        resp = JSONResponse({"access_token": token, "token_type": "bearer", "user": user_data})
        resp.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=secure_cookie,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        return resp
    except HTTPException:
        raise
    except Exception:
        logger.exception("Email login error")
        raise HTTPException(status_code=500, detail="Login failed. Please try again later.")

@router.post("/verify-email", response_model=EmailVerificationResponse)
def verify_user_email(token_data: TokenVerification, db: Session = Depends(get_db)):
    """Verify a user's email using a token."""
    try:
        result = verify_email(db, token_data.token)
        
        if result:
            return {"success": True, "message": "Email verified successfully"}
        else:
            return {"success": False, "message": "Invalid or expired verification link"}
    except Exception as e:
        logger.exception("Email verification error")
        raise HTTPException(status_code=500, detail="Email verification failed. Please try again later.")

@router.post("/request-verification", response_model=EmailVerificationResponse)
@limiter.limit("3/minute")
def request_email_verification(
    request: Request,
    req: EmailVerificationRequest, 
    db: Session = Depends(get_db)
):
    """Request a new verification email."""
    try:
        normalized_email = normalize_email(req.email)
        user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
        
        if not user:
            # Don't reveal that the email doesn't exist
            return {"success": True, "message": "If your email exists in our system, you will receive a verification link"}
        
        if user.is_verified:
            return {"success": True, "message": "Your email is already verified"}
        
        # Send verification email
        send_verification_email(db, user)
        
        return {
            "success": True, 
            "message": "If your email exists in our system, you will receive a verification link"
        }
    except Exception:
        logger.warning("Request verification failed due to internal error")
        # Don't reveal internal errors
        return {
            "success": True, 
            "message": "If your email exists in our system, you will receive a verification link"
        }


@router.post("/reset-password-request", response_model=EmailVerificationResponse)
@limiter.limit("3/minute")
def request_password_reset(
    request: Request,
    req: PasswordResetRequest, 
    db: Session = Depends(get_db)
):
    """Request a password reset link without revealing whether the email exists."""
    try:
        normalized_email = normalize_email(req.email)
        user = db.query(User).filter(func.lower(User.email) == normalized_email).first()

        if user:
            send_password_reset_email(db, user)

        return {
            "success": True,
            "message": "If your email exists in our system, you will receive a password reset link"
        }
    except Exception:
        logger.warning("Password reset request failed due to internal error")
        return {
            "success": True,
            "message": "If your email exists in our system, you will receive a password reset link"
        }


@router.post("/reset-password")
def confirm_password_reset(req: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Reset a user's password using a valid token."""
    try:
        ok = reset_password(db, req.token, req.password)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset link")

        return {"success": True, "message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Password reset confirmation error")
        raise HTTPException(status_code=500, detail="Password reset failed. Please try again later.")


@router.post("/logout")
def logout(response: Response):
    """Log out the current user by clearing the HttpOnly `access_token` cookie."""
    try:
        # Prepare response and delete cookie
        resp = JSONResponse({"success": True, "message": "Logged out"})
        # Ensure cookie deletion by instructing client to remove it
        resp.delete_cookie("access_token", path="/")
        return resp
    except Exception:
        logger.exception("Logout error")
        raise HTTPException(status_code=500, detail="Logout failed. Please try again.")

# Debug endpoint - REMOVE IN PRODUCTION
# @router.get("/check-user/{email}")
# def check_user_status(email: str, db: Session = Depends(get_db)):
#     """Debug endpoint to check user status."""
#     user = db.query(User).filter(User.email == email).first()
#     if not user:
#         return {"exists": False, "message": "User not found"}
    
#     return {
#         "exists": True,
#         "email": user.email,
#         "is_verified": user.is_verified,
#         "password_hash_length": len(user.password_hash) if user.password_hash else 0,
#         "id": user.id,
#         "created_at": user.created_at
#     }

# Standard OAuth2 login with form data
@router.post("/token")
@limiter.limit("10/minute")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Standard OAuth2 token endpoint."""
    try:
        normalized_email = normalize_email(form_data.username)
        user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
        if not user or not verify_password(form_data.password, user.password_hash):
            log_failed_auth_attempt(db, request, "/auth/token", normalized_email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified. Please check your inbox for a verification link.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = create_access_token(build_auth_token_payload(user))
        user_data = {"id": user.id, "email": user.email, "is_verified": user.is_verified}
        secure_cookie = settings.FRONTEND_URL.startswith("https")
        resp = JSONResponse({"access_token": token, "token_type": "bearer", "user": user_data})
        resp.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=secure_cookie,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        return resp
    except HTTPException:
        raise
    except Exception:
        logger.exception("OAuth token error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed. Please try again later.",
            headers={"WWW-Authenticate": "Bearer"},
        )
