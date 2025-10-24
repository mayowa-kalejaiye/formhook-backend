"""
Notification Pydantic schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class NotificationMetadata(BaseModel):
    """Flexible metadata for notifications"""
    formId: Optional[str] = None
    formName: Optional[str] = None
    submissionId: Optional[str] = None
    webhookUrl: Optional[str] = None
    status: Optional[str] = None
    emailTo: Optional[str] = None
    emailSubject: Optional[str] = None
    emailBody: Optional[str] = None
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None
    error: Optional[str] = None
    milestone: Optional[str] = None
    metric: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow additional fields


class NotificationOut(BaseModel):
    """Notification response schema"""
    id: str
    type: str
    priority: str
    title: str
    message: str
    timestamp: datetime
    read: bool
    archived: bool
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NotificationListResponse(BaseModel):
    """Response for list notifications endpoint"""
    notifications: list[NotificationOut]
    total: int
    unread: int


class NotificationCreate(BaseModel):
    """Schema for creating a notification"""
    type: str = Field(..., pattern="^(submission|webhook|system|email|security|milestone)$")
    priority: str = Field(..., pattern="^(low|medium|high|urgent)$")
    title: str = Field(..., max_length=255)
    message: str
    metadata: Optional[Dict[str, Any]] = None


class NotificationPreferencesOut(BaseModel):
    """Notification preferences response"""
    email_notifications: bool
    webhook_failures: bool
    security_alerts: bool
    milestone_alerts: bool
    submission_alerts: bool
    
    class Config:
        from_attributes = True


class NotificationPreferencesUpdate(BaseModel):
    """Update notification preferences"""
    email_notifications: Optional[bool] = None
    webhook_failures: Optional[bool] = None
    security_alerts: Optional[bool] = None
    milestone_alerts: Optional[bool] = None
    submission_alerts: Optional[bool] = None


class UnreadCountResponse(BaseModel):
    """Response for unread count endpoint"""
    count: int
