"""
Push notification Pydantic schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class PushSubscriptionKeys(BaseModel):
    """Keys for push subscription"""
    p256dh: str = Field(..., description="Public key for encryption")
    auth: str = Field(..., description="Authentication secret")


class PushSubscriptionCreate(BaseModel):
    """Schema for creating a push subscription"""
    endpoint: str = Field(..., description="Push service endpoint URL")
    keys: PushSubscriptionKeys = Field(..., description="Encryption keys")
    user_agent: Optional[str] = Field(None, description="Browser user agent")


class PushSubscriptionOut(BaseModel):
    """Schema for push subscription response"""
    id: int
    user_id: int
    endpoint: str
    created_at: datetime
    last_used: datetime

    class Config:
        from_attributes = True


class PushSubscriptionDelete(BaseModel):
    """Schema for deleting a push subscription"""
    endpoint: str = Field(..., description="Push service endpoint URL to delete")


class VapidKeyResponse(BaseModel):
    """Schema for VAPID public key response"""
    publicKey: str = Field(..., description="VAPID public key for frontend subscription")


class PushNotificationPayload(BaseModel):
    """
    Schema for push notification payload sent to browser
    Matches the format expected by the frontend service worker
    """
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification body/message")
    type: str = Field(
        ..., 
        description="Notification type: submission, webhook, system, email, security, milestone"
    )
    icon: Optional[str] = Field("/icon-192x192.png", description="Notification icon URL")
    badge: Optional[str] = Field("/badge-72x72.png", description="Badge icon URL")
    tag: Optional[str] = Field(None, description="Notification tag for grouping")
    url: Optional[str] = Field(None, description="URL to open when clicked")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    requireInteraction: bool = Field(False, description="Keep notification until user interacts")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "New Form Submission",
                "message": "Contact Form received a new submission",
                "type": "submission",
                "icon": "/icon-192x192.png",
                "badge": "/badge-72x72.png",
                "tag": "submission-123",
                "url": "/forms/form-456",
                "metadata": {
                    "formId": "form-456",
                    "submissionId": "sub-789"
                },
                "requireInteraction": False
            }
        }


class PushNotificationTest(BaseModel):
    """Schema for testing push notifications"""
    title: Optional[str] = Field("Test Notification", description="Test notification title")
    message: Optional[str] = Field("This is a test push notification from FormHook", description="Test message")
