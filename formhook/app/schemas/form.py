"""
Pydantic schemas for Form entity.
"""
from pydantic import BaseModel, EmailStr, AnyUrl
from typing import Optional
from datetime import datetime
import uuid

class FormBase(BaseModel):
    name: str
    description: Optional[str] = None
    webhook_url: Optional[AnyUrl] = None
    notification_email: Optional[EmailStr] = None

class FormCreate(FormBase):
    pass

class FormOut(FormBase):
    id: uuid.UUID
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True
