"""
Notification service for creating and managing notifications.
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict, Any
import logging
from ..models.notification import Notification, NotificationPreference
from ..models.form import Form
from ..schemas.push_notification import PushNotificationPayload

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating various types of notifications"""
    
    @staticmethod
    def _send_push_notification(db: Session, notification: Notification):
        """
        Internal helper to send push notification after creating in-app notification
        Uses lazy import to avoid circular dependencies
        """
        try:
            from .push_notification import PushNotificationService
            
            # Convert notification to push payload
            push_payload = PushNotificationPayload(
                title=notification.title,
                message=notification.message,
                type=notification.type,
                icon="/icon-192x192.png",
                badge="/badge-72x72.png",
                tag=f"{notification.type}-{notification.id}",
                url=f"/notifications",  # Default to notifications page
                metadata=notification.notification_metadata,
                requireInteraction=notification.priority == "urgent"
            )
            
            # Send push notification (async, doesn't block)
            result = PushNotificationService.send_push_notification(
                db=db,
                user_id=notification.user_id,
                notification_data=push_payload
            )
            logger.info(f"Push notification sent for notification {notification.id}: {result}")
        except Exception as e:
            # Don't fail the notification creation if push fails
            logger.error(f"Failed to send push notification: {e}")
    
    @staticmethod
    def create_submission_notification(
        db: Session,
        user_id: int,
        form_name: str,
        form_id: str,
        submission_id: int,
        submitter_email: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Create a notification for new form submission"""
        notification = Notification(
            user_id=user_id,
            type="submission",
            priority="medium",
            title=f"New submission for {form_name}",
            message=f"Received submission from {submitter_email or 'Anonymous'}",
            notification_metadata={
                "formId": form_id,
                "formName": form_name,
                "submissionId": str(submission_id),
                "ipAddress": ip_address
            }
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Send push notification
        NotificationService._send_push_notification(db, notification)
        
        return notification
    
    @staticmethod
    def create_webhook_failure_notification(
        db: Session,
        user_id: int,
        form_name: str,
        form_id: str,
        webhook_url: str,
        error: str
    ):
        """Create a notification for webhook delivery failure"""
        notification = Notification(
            user_id=user_id,
            type="webhook",
            priority="high",
            title="Webhook delivery failed",
            message=f"Failed to deliver webhook to {webhook_url}",
            notification_metadata={
                "formId": form_id,
                "formName": form_name,
                "webhookUrl": webhook_url,
                "status": "failed",
                "error": error
            }
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Send push notification for failures (high priority)
        NotificationService._send_push_notification(db, notification)
        
        return notification
    
    @staticmethod
    def create_webhook_success_notification(
        db: Session,
        user_id: int,
        form_name: str,
        form_id: str,
        webhook_url: str
    ):
        """Create a notification for successful webhook delivery"""
        notification = Notification(
            user_id=user_id,
            type="webhook",
            priority="low",
            title="Webhook delivered successfully",
            message=f"Webhook successfully delivered to {webhook_url}",
            notification_metadata={
                "formId": form_id,
                "formName": form_name,
                "webhookUrl": webhook_url,
                "status": "success"
            }
        )
        db.add(notification)
        db.commit()
        return notification
    
    @staticmethod
    def create_email_notification(
        db: Session,
        user_id: int,
        email_to: str,
        email_subject: str,
        status: str,
        form_id: Optional[str] = None,
        form_name: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Create a notification for email sent/failed"""
        priority = "high" if status == "failed" else "low"
        title = "Email delivery failed" if status == "failed" else "Email sent successfully"
        message = f"Email to {email_to}: {email_subject}"
        
        notification = Notification(
            user_id=user_id,
            type="email",
            priority=priority,
            title=title,
            message=message,
            notification_metadata={
                "emailTo": email_to,
                "emailSubject": email_subject,
                "formId": form_id,
                "formName": form_name,
                "status": status,
                "error": error
            }
        )
        db.add(notification)
        db.commit()
        return notification
    
    @staticmethod
    def create_security_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Create a security notification"""
        notification = Notification(
            user_id=user_id,
            type="security",
            priority="urgent",
            title=title,
            message=message,
            notification_metadata={
                "ipAddress": ip_address,
                "userAgent": user_agent
            }
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Send push notification for security alerts (urgent)
        NotificationService._send_push_notification(db, notification)
        
        return notification
    
    @staticmethod
    def create_milestone_notification(
        db: Session,
        user_id: int,
        form_name: str,
        form_id: str,
        milestone: int,
        metric: str = "submissions"
    ):
        """Create a milestone notification"""
        notification = Notification(
            user_id=user_id,
            type="milestone",
            priority="medium",
            title=f"Milestone reached! 🎉",
            message=f"Your {form_name} just received its {milestone}th {metric}!",
            notification_metadata={
                "formId": form_id,
                "formName": form_name,
                "milestone": str(milestone),
                "metric": metric
            }
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Send push notification for milestones
        NotificationService._send_push_notification(db, notification)
        
        return notification
    
    @staticmethod
    def create_system_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        form_id: Optional[str] = None,
        form_name: Optional[str] = None
    ):
        """Create a system notification"""
        notification = Notification(
            user_id=user_id,
            type="system",
            priority="low",
            title=title,
            message=message,
            notification_metadata={
                "formId": form_id,
                "formName": form_name
            }
        )
        db.add(notification)
        db.commit()
        return notification
    
    @staticmethod
    def check_milestone(db: Session, form_id: str, submission_count: int):
        """Check if a milestone has been reached and create notification"""
        milestones = [100, 500, 1000, 5000, 10000]
        
        if submission_count in milestones:
            form = db.query(Form).filter(Form.id == form_id).first()
            if form:
                NotificationService.create_milestone_notification(
                    db=db,
                    user_id=form.user_id,
                    form_name=form.name,
                    form_id=form_id,
                    milestone=submission_count
                )
    
    @staticmethod
    def get_or_create_preferences(db: Session, user_id: int) -> NotificationPreference:
        """Get or create notification preferences for a user"""
        prefs = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).first()
        
        if not prefs:
            prefs = NotificationPreference(
                user_id=user_id,
                email_notifications=True,
                webhook_failures=True,
                security_alerts=True,
                milestone_alerts=True,
                submission_alerts=True
            )
            db.add(prefs)
            db.commit()
            db.refresh(prefs)
        
        return prefs
