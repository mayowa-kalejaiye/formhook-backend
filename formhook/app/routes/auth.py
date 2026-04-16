"""
Auth routes: signup, login, and email verification.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta
from ..schemas.user import UserCreate, UserOut
from ..models.user import User
from ..core.database import SessionLocal
from ..core.security import hash_password, verify_password, create_access_token
from ..schemas.verification import EmailVerificationRequest, EmailVerificationResponse, TokenVerification
from ..services.verification import verify_email, send_verification_email
from pydantic import EmailStr, BaseModel
import os
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from ..core.config import settings
from ..core.utils import now_utc

router = APIRouter()


def normalize_email(value: str) -> str:
    return value.strip().lower()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", response_model=UserOut)
async def signup(
    request: Request,
    email: str = Form(None),
    password: str = Form(None),
    db: Session = Depends(get_db)
):
    """Register a new user and send verification email. Accepts both form data and JSON."""
    try:
        print(f"Signup request content type: {request.headers.get('content-type', 'unknown')}")
        
        # Try to get data from form first
        if email is not None and password is not None:
            # Form data was provided
            user_email = email
            user_password = password
            print("Using form data for signup")
        else:
            # Try to parse JSON body
            try:
                body = await request.json()
                print(f"Signup request JSON body: {body}")
                user_email = body.get("email")
                user_password = body.get("password")
                
                if not user_email or not user_password:
                    raise HTTPException(
                        status_code=422,
                        detail="Missing required fields: email and password"
                    )
            except Exception as e:
                # If we can't parse JSON and don't have form data, raise error
                print(f"Failed to parse signup request body: {str(e)}")
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
                print(f"Error sending verification email: {e}")
        
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        # Log any other errors
        print(f"Signup error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed. Please try again later.")
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log any other errors
        print(f"Signup error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error during signup: {str(e)}")


# Pydantic model for login request
class LoginRequest(BaseModel):
    email: str  # Changed to match the React form field name
    password: str

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(None), 
    password: str = Form(None),
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT. Accepts both form data and JSON."""
    try:
        print(f"Request content type: {request.headers.get('content-type', 'unknown')}")
        
        # Try to get data from form first
        if email is not None and password is not None:
            # Form data was provided
            user_email = email
            user_password = password
            print("Using form data for login")
        else:
            # Try to parse JSON body
            try:
                body = await request.json()
                print(f"Request JSON body: {body}")
                user_email = body.get("email")
                user_password = body.get("password")
                
                if not user_email or not user_password:
                    raise HTTPException(
                        status_code=422,
                        detail="Missing required fields: email and password"
                    )
            except Exception as e:
                # If we can't parse JSON and don't have form data, raise error
                print(f"Failed to parse request body: {str(e)}")
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

        print(f"Login attempt for email: {user_email}")
        
        # Find the user
        user = db.query(User).filter(func.lower(User.email) == user_email).first()
        if not user or not verify_password(user_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        
        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified. Please check your inbox for a verification link."
            )
        
        token = create_access_token({"sub": str(user.id), "email": user.email})
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
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login failed. Please try again later.")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

# Email login model
class EmailLoginRequest(BaseModel):
    email: str  # Changed from EmailStr to str for more flexibility
    password: str

@router.post("/email-login")
def email_login(request: EmailLoginRequest, db: Session = Depends(get_db)):
    """Alternative login endpoint accepting 'email' instead of 'username'."""
    try:
        normalized_email = normalize_email(request.email)
        user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        
        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified. Please check your inbox for a verification link."
            )
        
        token = create_access_token({"sub": str(user.id), "email": user.email})
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
    except Exception as e:
        print(f"Email login error: {str(e)}")
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
        print(f"Email verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Email verification failed. Please try again later.")

@router.post("/request-verification", response_model=EmailVerificationResponse)
def request_email_verification(
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
    except Exception as e:
        print(f"Request verification error: {str(e)}")
        # Don't reveal internal errors
        return {
            "success": True, 
            "message": "If your email exists in our system, you will receive a verification link"
        }


@router.post("/logout")
def logout(response: Response):
    """Log out the current user by clearing the HttpOnly `access_token` cookie."""
    try:
        # Prepare response and delete cookie
        resp = JSONResponse({"success": True, "message": "Logged out"})
        # Ensure cookie deletion by instructing client to remove it
        resp.delete_cookie("access_token", path="/")
        return resp
    except Exception as e:
        print(f"Logout error: {e}")
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
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Standard OAuth2 token endpoint."""
    try:
        normalized_email = normalize_email(form_data.username)
        user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
        if not user or not verify_password(form_data.password, user.password_hash):
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
        
        token = create_access_token({"sub": str(user.id), "email": user.email})
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
    except Exception as e:
        print(f"OAuth token error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed. Please try again later.",
            headers={"WWW-Authenticate": "Bearer"},
        )
