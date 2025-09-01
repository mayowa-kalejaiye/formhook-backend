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
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    db_user = User(email=user.email, password_hash=hash_password(user.password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Get base URL or use environment variable
    base_url = str(request.base_url)
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    
    # Use frontend URL from environment or fallback to base URL
    frontend_url = os.getenv("FRONTEND_URL", base_url)
    
    # Send verification email
    send_verification_email(db, db_user, frontend_url)
    
    return db_user


# Pydantic model for login request
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT."""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # Check if email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=401,
            detail="Email not verified. Please check your inbox for a verification link."
        )
    
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
    request: Request,
    db: Session = Depends(get_db)
):
    """Request a new verification email."""
    user = db.query(User).filter(User.email == req.email).first()
    
    if not user:
        # Don't reveal that the email doesn't exist
        return {"success": True, "message": "If your email exists in our system, you will receive a verification link"}
    
    if user.is_verified:
        return {"success": True, "message": "Your email is already verified"}
    
    # Get base URL from request
    base_url = str(request.base_url)
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    
    # Frontend URL from environment or config
    frontend_url = os.getenv("FRONTEND_URL", base_url)
    
    result = send_verification_email(db, user, frontend_url)
    
    return {
        "success": True, 
        "message": "If your email exists in our system, you will receive a verification link"
    }
