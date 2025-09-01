"""
Pydantic schemas for User entity.
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    created_at: datetime
    is_verified: bool = False
    api_token_hash: Optional[str] = None
    token_created_at: Optional[datetime] = None

    class Config:
        orm_mode = True
