"""
Push notification service for browser push notifications
Handles subscription management and sending push notifications
"""
from sqlalchemy.orm import Session
from pywebpush import webpush, WebPushException
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from ..models.push_subscription import PushSubscription
from ..models.notification import NotificationPreference
from ..schemas.push_notification import PushNotificationPayload
from ..core.config import settings

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Service for managing push notifications"""

    @staticmethod
    def subscribe(
        db: Session,
        user_id: int,
        endpoint: str,
        p256dh: str,
        auth: str,
        user_agent: Optional[str] = None
    ) -> PushSubscription:
        """
        Subscribe user to push notifications
        Creates or updates existing subscription
        """
        # Check if subscription already exists
        existing_sub = db.query(PushSubscription).filter(
            PushSubscription.endpoint == endpoint
        ).first()

        if existing_sub:
            # Update existing subscription
            existing_sub.p256dh = p256dh
            existing_sub.auth = auth
            existing_sub.user_agent = user_agent
            existing_sub.last_used = datetime.utcnow()
            db.commit()
            db.refresh(existing_sub)
            logger.info(f"Updated push subscription for user {user_id}")
            return existing_sub
        
        # Create new subscription
        subscription = PushSubscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=user_agent
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        logger.info(f"Created new push subscription for user {user_id}")
        return subscription

    @staticmethod
    def unsubscribe(db: Session, user_id: int, endpoint: str) -> bool:
        """
        Unsubscribe user from push notifications
        Returns True if subscription was deleted, False if not found
        """
        subscription = db.query(PushSubscription).filter(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint
        ).first()

        if subscription:
            db.delete(subscription)
            db.commit()
            logger.info(f"Deleted push subscription for user {user_id}")
            return True
        
        logger.warning(f"Push subscription not found for user {user_id} and endpoint {endpoint[:50]}")
        return False

    @staticmethod
    def get_user_subscriptions(db: Session, user_id: int) -> List[PushSubscription]:
        """Get all push subscriptions for a user"""
        return db.query(PushSubscription).filter(
            PushSubscription.user_id == user_id
        ).all()

    @staticmethod
    def send_push_notification(
        db: Session,
        user_id: int,
        notification_data: PushNotificationPayload
    ) -> Dict[str, Any]:
        """
        Send push notification to all user's subscriptions
        Returns statistics about success/failure
        """
        # Check if VAPID keys are configured
        if not settings.VAPID_PUBLIC_KEY or not settings.VAPID_PRIVATE_KEY:
            logger.error("VAPID keys not configured. Push notifications disabled.")
            return {
                "sent": 0,
                "failed": 0,
                "deleted": 0,
                "error": "VAPID keys not configured"
            }

        # Check user preferences
        preferences = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).first()

        # If user has disabled push notifications, skip
        if preferences and not preferences.email_notifications:
            logger.info(f"User {user_id} has disabled push notifications")
            return {
                "sent": 0,
                "failed": 0,
                "deleted": 0,
                "skipped": True
            }

        # Get all subscriptions for user
        subscriptions = PushNotificationService.get_user_subscriptions(db, user_id)
        
        if not subscriptions:
            logger.info(f"No push subscriptions found for user {user_id}")
            return {
                "sent": 0,
                "failed": 0,
                "deleted": 0,
                "no_subscriptions": True
            }

        sent = 0
        failed = 0
        deleted = 0

        # Send to each subscription
        for subscription in subscriptions:
            try:
                # Prepare subscription info for pywebpush
                subscription_info = {
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth
                    }
                }

                # Convert notification data to JSON
                payload = notification_data.model_dump_json()

                # Send push notification
                webpush(
                    subscription_info=subscription_info,
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={
                        "sub": settings.VAPID_SUBJECT
                    }
                )

                # Update last_used timestamp
                subscription.last_used = datetime.utcnow()
                db.commit()
                
                sent += 1
                logger.info(f"Push notification sent successfully to subscription {subscription.id}")

            except WebPushException as e:
                logger.error(f"Push notification failed for subscription {subscription.id}: {e}")
                failed += 1

                # If subscription is expired or invalid (410 Gone or 404 Not Found), delete it
                if hasattr(e, 'response') and e.response and e.response.status_code in [404, 410]:
                    logger.info(f"Deleting invalid subscription {subscription.id}")
                    db.delete(subscription)
                    db.commit()
                    deleted += 1

            except Exception as e:
                logger.error(f"Unexpected error sending push notification: {e}")
                failed += 1

        return {
            "sent": sent,
            "failed": failed,
            "deleted": deleted,
            "total_subscriptions": len(subscriptions)
        }

    @staticmethod
    def send_test_notification(db: Session, user_id: int, title: str = "Test Notification", message: str = "This is a test") -> Dict[str, Any]:
        """Send a test push notification to user"""
        notification_data = PushNotificationPayload(
            title=title,
            message=message,
            type="system",
            icon="/icon-192x192.png",
            url="/notifications"
        )
        return PushNotificationService.send_push_notification(db, user_id, notification_data)

    @staticmethod
    def cleanup_expired_subscriptions(db: Session, days: int = 90) -> int:
        """
        Clean up subscriptions that haven't been used in X days
        Returns number of deleted subscriptions
        """
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        expired = db.query(PushSubscription).filter(
            PushSubscription.last_used < cutoff_date
        ).all()

        count = len(expired)
        for subscription in expired:
            db.delete(subscription)
        
        db.commit()
        logger.info(f"Cleaned up {count} expired push subscriptions")
        return count
