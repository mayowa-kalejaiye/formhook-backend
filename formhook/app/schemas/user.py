"""
Pydantic schemas for User entity.
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

from typing import Optional

class UserOut(UserBase):
    id: int
    created_at: datetime
    api_token_hash: Optional[str] = None
    token_created_at: Optional[datetime] = None

    class Config:
        orm_mode = True
