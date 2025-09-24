"""
Pydantic schemas for Submission entity.
"""
from pydantic import BaseModel, field_serializer
from typing import Dict, Any
from datetime import datetime
from uuid import UUID

class SubmissionBase(BaseModel):
    data: Dict[str, Any]
    ip_address: str

class SubmissionCreate(BaseModel):
    """Schema for creating submissions - only requires data field."""
    data: Dict[str, Any]

class SubmissionOut(SubmissionBase):
    id: int
    form_id: str
    created_at: datetime
    country: str | None = None
    region: str | None = None
    city: str | None = None
    location_source: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    threat_score: int | None = None

    @field_serializer('form_id')
    def serialize_form_id(self, form_id: UUID | str) -> str:
        """Convert UUID to string for serialization."""
        return str(form_id)

    class Config:
        from_attributes = True
