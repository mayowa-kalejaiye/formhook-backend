"""
Schemas for email verification.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional

class EmailVerificationRequest(BaseModel):
    email: EmailStr

class EmailVerificationResponse(BaseModel):
    success: bool
    message: str

class TokenVerification(BaseModel):
    token: str
