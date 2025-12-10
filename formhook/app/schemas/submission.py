"""
Pydantic schemas for Submission entity.
"""
from pydantic import BaseModel, validator
from typing import Dict, Any, Union
from datetime import datetime
from uuid import UUID
import json

from ..core.config import settings

class SubmissionBase(BaseModel):
    data: Dict[str, Any]
    ip_address: str

class SubmissionCreate(BaseModel):
    """Schema for creating submissions - only requires data field."""
    data: Dict[str, Any]

    @validator('data')
    def validate_submission_data(cls, v):
        # Must be a dict
        if not isinstance(v, dict):
            raise ValueError('data must be an object/dictionary')

        # Field count limit
        if len(v) > settings.SUBMISSION_MAX_FIELDS:
            raise ValueError(f'data has too many fields (max {settings.SUBMISSION_MAX_FIELDS})')

        # Ensure keys are strings
        for key in v.keys():
            if not isinstance(key, str):
                raise ValueError('all keys in data must be strings')

        # Size limit: JSON serialized length
        try:
            size = len(json.dumps(v, ensure_ascii=False).encode('utf-8'))
        except Exception:
            raise ValueError('data must be JSON serializable')
        if size > settings.SUBMISSION_MAX_SIZE_BYTES:
            raise ValueError(f'data exceeds maximum size of {settings.SUBMISSION_MAX_SIZE_BYTES} bytes')

        return v

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
    device_type: str | None = None
    user_agent: str | None = None

    @validator('form_id', pre=True)
    def convert_form_id_to_string(cls, v):
        """Convert UUID to string if needed."""
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
