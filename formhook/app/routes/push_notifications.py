"""
Push notification routes
Endpoints for managing browser push notification subscriptions
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List

from ..core.database import get_db
from ..dependencies import get_current_user
from ..models.user import User
from ..models.push_subscription import PushSubscription
from ..services.push_notification import PushNotificationService
from ..schemas.push_notification import (
    PushSubscriptionCreate,
    PushSubscriptionOut,
    PushSubscriptionDelete,
    VapidKeyResponse,
    PushNotificationTest
)
from ..core.config import settings

router = APIRouter()


@router.post("/subscribe", response_model=dict)
async def subscribe_to_push(
    subscription: PushSubscriptionCreate,
    user_agent: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Subscribe user to push notifications
    Stores the browser's push subscription info
    """
    try:
        push_sub = PushNotificationService.subscribe(
            db=db,
            user_id=current_user.id,
            endpoint=subscription.endpoint,
            p256dh=subscription.keys.p256dh,
            auth=subscription.keys.auth,
            user_agent=user_agent or subscription.user_agent
        )
        
        return {
            "success": True,
            "message": "Successfully subscribed to push notifications",
            "subscription_id": push_sub.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to subscribe: {str(e)}")


@router.post("/unsubscribe", response_model=dict)
async def unsubscribe_from_push(
    subscription: PushSubscriptionDelete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Unsubscribe user from push notifications
    Removes the browser's push subscription
    """
    success = PushNotificationService.unsubscribe(
        db=db,
        user_id=current_user.id,
        endpoint=subscription.endpoint
    )
    
    if success:
        return {
            "success": True,
            "message": "Successfully unsubscribed from push notifications"
        }
    else:
        return {
            "success": False,
            "message": "Subscription not found"
        }


@router.get("/vapid-key", response_model=VapidKeyResponse)
async def get_vapid_public_key():
    """
    Get VAPID public key for push subscription
    Required by frontend to subscribe to push notifications
    """
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(
            status_code=503,
            detail="Push notifications are not configured on this server"
        )
    
    return VapidKeyResponse(publicKey=settings.VAPID_PUBLIC_KEY)


@router.get("/subscriptions", response_model=List[PushSubscriptionOut])
async def get_user_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all push subscriptions for current user
    Useful for managing multiple devices
    """
    subscriptions = PushNotificationService.get_user_subscriptions(
        db=db,
        user_id=current_user.id
    )
    return subscriptions


@router.delete("/subscriptions/{subscription_id}", response_model=dict)
async def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific push subscription by ID
    Useful for managing multiple devices
    """
    subscription = db.query(PushSubscription).filter(
        PushSubscription.id == subscription_id,
        PushSubscription.user_id == current_user.id
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    db.delete(subscription)
    db.commit()

    return {
        "success": True,
        "message": "Subscription deleted successfully"
    }


@router.post("/test", response_model=dict)
async def send_test_notification(
    test_data: Optional[PushNotificationTest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a test push notification to current user
    Useful for testing push notification setup
    """
    if test_data is None:
        test_data = PushNotificationTest()

    result = PushNotificationService.send_test_notification(
        db=db,
        user_id=current_user.id,
        title=test_data.title,
        message=test_data.message
    )

    if result.get("sent", 0) > 0:
        return {
            "success": True,
            "message": f"Test notification sent to {result['sent']} device(s)",
            "details": result
        }
    elif result.get("no_subscriptions"):
        raise HTTPException(
            status_code=404,
            detail="No push subscriptions found. Please enable push notifications first."
        )
    elif result.get("error"):
        raise HTTPException(
            status_code=503,
            detail=result["error"]
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to send test notification"
        )
