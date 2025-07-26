from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class WebhookDeliveryLogOut(BaseModel):
    id: int
    form_id: Optional[str]
    submission_id: int
    webhook_url: str
    status: str
    attempts: int
    last_attempt_at: Optional[datetime]
    next_retry_at: Optional[datetime]
    response_code: Optional[int]
    error_message: Optional[str]
    success: Optional[bool]
    headers_sent: Optional[Dict]
    response_body: Optional[str]
    retry_count: Optional[int]
    duration_ms: Optional[int]

    class Config:
        from_attributes = True
