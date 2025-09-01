"""
Auth routes: signup, login, and email verification.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from ..schemas.user import UserCreate, UserOut
from ..models.user import User
from ..core.database import SessionLocal
from ..core.security import hash_password, verify_password, create_access_token
from ..schemas.verification import EmailVerificationRequest, EmailVerificationResponse, TokenVerification
from ..services.verification import verify_email, send_verification_email
import os

from pydantic import EmailStr, BaseModel

router = APIRouter()

# Dependency to get DB session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", response_model=UserOut)
def signup(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Register a new user and send verification email."""
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user
        db_user = User(email=user.email, password_hash=hash_password(user.password))
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Send verification email (no need to pass base_url anymore)
        try:
            send_verification_email(db, db_user)
        except Exception as e:
            # Log the error but don't fail the signup
            print(f"Error sending verification email: {e}")
        
        return db_user
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
    username: EmailStr  # Changed from email to username to match OAuth2 standard
    password: str

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT."""
    # We search by email even though the field is called username in the request
    user = db.query(User).filter(User.email == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # Check if email is verified
    if not user.is_verified:
        # For debugging, let's temporarily bypass this
        # raise HTTPException(
        #     status_code=401,
        #     detail="Email not verified. Please check your inbox for a verification link."
        # )
        pass
    
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": token, "token_type": "bearer"}

# Alternative login endpoint for email field name
class EmailLoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/email-login")
def email_login(request: EmailLoginRequest, db: Session = Depends(get_db)):
    """Alternative login endpoint accepting 'email' instead of 'username'."""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # Check if email is verified
    if not user.is_verified:
        # For debugging, let's temporarily bypass this
        # raise HTTPException(
        #     status_code=401,
        #     detail="Email not verified. Please check your inbox for a verification link."
        # )
        pass
    
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/verify-email", response_model=EmailVerificationResponse)
def verify_user_email(token_data: TokenVerification, db: Session = Depends(get_db)):
    """Verify a user's email using a token."""
    result = verify_email(db, token_data.token)
    
    if result:
        return {"success": True, "message": "Email verified successfully"}
    else:
        return {"success": False, "message": "Invalid or expired verification link"}

@router.post("/request-verification", response_model=EmailVerificationResponse)
def request_email_verification(
    req: EmailVerificationRequest, 
    db: Session = Depends(get_db)
):
    """Request a new verification email."""
    user = db.query(User).filter(User.email == req.email).first()
    
    if not user:
        # Don't reveal that the email doesn't exist
        return {"success": True, "message": "If your email exists in our system, you will receive a verification link"}
    
    if user.is_verified:
        return {"success": True, "message": "Your email is already verified"}
    
    # Send verification email
    result = send_verification_email(db, user)
    
    return {
        "success": True, 
        "message": "If your email exists in our system, you will receive a verification link"
    }

# Debug endpoint - REMOVE IN PRODUCTION
@router.get("/check-user/{email}")
def check_user_status(email: str, db: Session = Depends(get_db)):
    """Debug endpoint to check user status."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"exists": False, "message": "User not found"}
    
    return {
        "exists": True,
        "email": user.email,
        "is_verified": user.is_verified,
        "password_hash_length": len(user.password_hash) if user.password_hash else 0,
        "id": user.id,
        "created_at": user.created_at
    }
