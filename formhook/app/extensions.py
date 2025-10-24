from slowapi import Limiter
from slowapi.util import get_remote_address
from .core.config import settings
from fastapi import Request
from typing import Optional

def get_user_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting based on authentication status.
    Authenticated users get identified by user ID, anonymous by IP.
    """
    # Check if user is authenticated by looking for user in request state
    if hasattr(request.state, 'user') and request.state.user:
        # Authenticated user - use user ID for higher limits
        return f"user:{request.state.user.id}"
    
    # Unauthenticated - use IP address
    return f"ip:{get_remote_address(request)}"

# Default rate limits: 10/minute for unauthenticated, will be overridden for authenticated
limiter = Limiter(key_func=get_user_identifier, default_limits=[settings.RATE_LIMIT])

