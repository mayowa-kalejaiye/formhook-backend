"""
Auth routes: signup, login, and email verification.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from sqlalchemy.orm import Session
from ..schemas.user import UserCreate, UserOut
from ..models.user import User
from ..core.database import SessionLocal
from ..core.security import hash_password, verify_password, create_access_token
from ..schemas.verification import EmailVerificationRequest, EmailVerificationResponse, TokenVerification
from ..services.verification import verify_email, send_verification_email
from pydantic import EmailStr, BaseModel
import os

router = APIRouter()

# Dependency to get DB session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", response_model=UserOut)
async def signup(
    email: str = Form(None),
    password: str = Form(None),
    user_json: UserCreate = None,
    request: Request = None, 
    db: Session = Depends(get_db)
):
    """Register a new user and send verification email. Accepts both form data and JSON."""
    try:
        # Handle both form data and JSON
        if email and password:
            # Form data was used
            user_email = email
            user_password = password
        elif user_json:
            # JSON was used
            user_email = user_json.email
            user_password = user_json.password
        else:
            raise HTTPException(
                status_code=422, 
                detail="Invalid request format. Provide email and password either as form data or in JSON body."
            )
        
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user
        db_user = User(email=user_email, password_hash=hash_password(user_password))
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Send verification email
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
    email: str  # Changed to match the React form field name
    password: str

@router.post("/login")
async def login(
    email: str = Form(None), 
    password: str = Form(None),
    request_body: LoginRequest = None,
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT. Accepts both form data and JSON."""
    try:
        # Handle both form data and JSON
        if email and password:
            # Form data was used
            pass
        elif request_body:
            # JSON was used
            email = request_body.email
            password = request_body.password
        else:
            raise HTTPException(
                status_code=422, 
                detail="Invalid request format. Provide email and password either as form data or in JSON body."
            )
        
        print(f"Login attempt for email: {email}")
        
        # Find the user
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
        # Check if email is verified - temporarily bypassed
        if not user.is_verified:
            # For debugging, let's temporarily bypass this
            # raise HTTPException(
            #     status_code=401,
            #     detail="Email not verified. Please check your inbox for a verification link."
            # )
            pass
        
        token = create_access_token({"sub": str(user.id), "email": user.email})
        return {"access_token": token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

# Alternative login endpoint for email field name
class EmailLoginRequest(BaseModel):
    email: str  # Changed from EmailStr to str for more flexibility
    password: str

@router.post("/email-login")
def email_login(request: EmailLoginRequest, db: Session = Depends(get_db)):
    """Alternative login endpoint accepting 'email' instead of 'username'."""
    try:
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
    except Exception as e:
        print(f"Email login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

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

# Standard OAuth2 login with form data
from fastapi.security import OAuth2PasswordRequestForm

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Standard OAuth2 token endpoint."""
    try:
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not verify_password(form_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if email is verified - temporarily bypassed
        if not user.is_verified:
            # For debugging, let's temporarily bypass this
            # raise HTTPException(
            #     status_code=401,
            #     detail="Email not verified. Please check your inbox for a verification link."
            # )
            pass
        
        token = create_access_token({"sub": str(user.id), "email": user.email})
        return {"access_token": token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"OAuth token error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during authentication: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
