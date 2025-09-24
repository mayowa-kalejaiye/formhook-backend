"""
Pydantic schemas for Submission entity.
"""
from pydantic import BaseModel, validator
from typing import Dict, Any, Union
from datetime import datetime
from uuid import UUID

class SubmissionBase(BaseModel):
    data: Dict[str, Any]
    ip_address: str

class SubmissionCreate(BaseModel):
    """Schema for creating submissions - only requires data field."""
    data: Dict[str, Any]

class SubmissionOut(BaseModel):
    id: int
    form_id: str
    data: Dict[str, Any]
    ip_address: str
    created_at: datetime
    country: str | None = None
    region: str | None = None
    city: str | None = None
    location_source: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    threat_score: int | None = None

    @validator('form_id', pre=True)
    def convert_form_id_to_string(cls, v):
        """Convert UUID to string if needed."""
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
