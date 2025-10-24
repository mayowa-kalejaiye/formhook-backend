"""
Notification routes for FormHook.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import Optional, List
from datetime import datetime

from ..dependencies import get_db, get_current_user
from ..models.user import User
from ..models.notification import Notification, NotificationPreference
from ..schemas.notification import (
    NotificationOut,
    NotificationListResponse,
    NotificationPreferencesOut,
    NotificationPreferencesUpdate,
    UnreadCountResponse
)
from ..services.notification import NotificationService

router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
def get_notifications(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    type: Optional[str] = Query(None),
    read: Optional[bool] = Query(None),
    archived: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all notifications for the authenticated user with pagination and filtering.
    
    Query Parameters:
    - limit: Maximum number of notifications to return (1-500, default: 100)
    - offset: Number of notifications to skip (default: 0)
    - type: Filter by notification type (submission, webhook, system, email, security, milestone)
    - read: Filter by read status (true/false)
    - archived: Filter by archived status (true/false)
    """
    # Build query
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    # Apply filters
    if type:
        query = query.filter(Notification.type == type)
    if read is not None:
        query = query.filter(Notification.read == read)
    if archived is not None:
        query = query.filter(Notification.archived == archived)
    else:
        # By default, exclude archived unless explicitly requested
        query = query.filter(Notification.archived == False)
    
    # Get total count
    total = query.count()
    
    # Get unread count
    unread = db.query(Notification).filter(
        and_(
            Notification.user_id == current_user.id,
            Notification.read == False,
            Notification.archived == False
        )
    ).count()
    
    # Apply pagination and ordering
    notifications = query.order_by(desc(Notification.timestamp)).offset(offset).limit(limit).all()
    
    # Convert to response format
    notification_list = []
    for notif in notifications:
        notification_list.append(NotificationOut(
            id=str(notif.id),
            type=notif.type,
            priority=notif.priority,
            title=notif.title,
            message=notif.message,
            timestamp=notif.timestamp,
            read=notif.read,
            archived=notif.archived,
            metadata=notif.notification_metadata
        ))
    
    return NotificationListResponse(
        notifications=notification_list,
        total=total,
        unread=unread
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get count of unread notifications for the authenticated user.
    Fast endpoint for displaying badge counts.
    """
    count = db.query(Notification).filter(
        and_(
            Notification.user_id == current_user.id,
            Notification.read == False,
            Notification.archived == False
        )
    ).count()
    
    return UnreadCountResponse(count=count)


@router.post("/{notification_id}/read")
def mark_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a specific notification as read"""
    notification = db.query(Notification).filter(
        and_(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.read = True
    db.commit()
    
    return {"success": True}


@router.post("/mark-all-read")
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all notifications as read for the authenticated user"""
    db.query(Notification).filter(
        and_(
            Notification.user_id == current_user.id,
            Notification.read == False
        )
    ).update({"read": True})
    
    db.commit()
    
    return {"success": True}


@router.post("/{notification_id}/archive")
def archive_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Archive a notification (hide from main view)"""
    notification = db.query(Notification).filter(
        and_(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.archived = True
    notification.read = True  # Also mark as read when archiving
    db.commit()
    
    return {"success": True}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permanently delete a notification"""
    notification = db.query(Notification).filter(
        and_(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    
    return {"success": True}


@router.get("/preferences", response_model=NotificationPreferencesOut)
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notification preferences for the authenticated user"""
    prefs = NotificationService.get_or_create_preferences(db, current_user.id)
    return prefs


@router.put("/preferences")
def update_preferences(
    preferences: NotificationPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update notification preferences for the authenticated user"""
    prefs = NotificationService.get_or_create_preferences(db, current_user.id)
    
    # Update only provided fields
    if preferences.email_notifications is not None:
        prefs.email_notifications = preferences.email_notifications
    if preferences.webhook_failures is not None:
        prefs.webhook_failures = preferences.webhook_failures
    if preferences.security_alerts is not None:
        prefs.security_alerts = preferences.security_alerts
    if preferences.milestone_alerts is not None:
        prefs.milestone_alerts = preferences.milestone_alerts
    if preferences.submission_alerts is not None:
        prefs.submission_alerts = preferences.submission_alerts
    
    db.commit()
    
    return {"success": True}
