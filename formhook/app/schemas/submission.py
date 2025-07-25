"""
Pydantic schemas for Submission entity.
"""
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

class SubmissionBase(BaseModel):
    data: Dict[str, Any]
    ip_address: str

class SubmissionCreate(SubmissionBase):
    pass

class SubmissionOut(SubmissionBase):
    id: int
    form_id: str
    created_at: datetime

    class Config:
        orm_mode = True
