"""
Pydantic schemas for Form entity.
"""

from pydantic import BaseModel, EmailStr, AnyUrl, Field, model_validator
from typing import Optional, List, Literal
from datetime import datetime
import uuid

class FormField(BaseModel):
    name: str
    label: str
    type: Literal["text", "email", "textarea", "checkbox", "select"]
    required: bool


class FormBase(BaseModel):
    name: str
    description: Optional[str] = None
    webhook_url: Optional[AnyUrl] = None
    webhook_headers: Optional[dict] = None
    webhook_secret: Optional[str] = None
    notification_email: Optional[EmailStr] = None
    redirect_url: Optional[AnyUrl] = None
    success_message: Optional[str] = None
    fields: List[FormField] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_fields(self):
        fields = self.fields
        if fields is not None:
            if not isinstance(fields, list):
                raise ValueError("fields must be a list of field definitions")
            for f in fields:
                if not isinstance(f, FormField):
                    raise ValueError("Each field must be a FormField object")
        return self

class FormCreate(FormBase):
    pass

class FormOut(FormBase):
    id: uuid.UUID
    user_id: int
    created_at: datetime
    api_token: Optional[str] = Field(
        default=None,
        description="Hashed API token for form submissions. Only returned on generation.",
        exclude=True
    )
    require_token: bool = Field(
        default=False,
        description="If true, submissions require a valid API token in the Authorization header."
    )

    class Config:
        from_attributes = True

class FormWithMetadata(FormOut):
    """Form schema with additional metadata like submission counts."""
    submission_count: int = Field(
        default=0,
        description="Total number of submissions for this form"
    )
    recent_submissions: int = Field(
        default=0,
        description="Number of submissions in the last 7 days"
    )
    last_submission_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the most recent submission"
    )
    status: str = Field(
        default="active",
        description="Form status: active, draft, archived"
    )

    class Config:
        from_attributes = True
