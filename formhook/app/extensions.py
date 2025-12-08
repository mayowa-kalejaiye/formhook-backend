from slowapi import Limiter
from slowapi.util import get_remote_address
from .core.config import settings
from fastapi import Request
from typing import Optional

# Try to import token decoder to identify users from Bearer tokens when possible
try:
    from .core.security import decode_access_token
except Exception:
    decode_access_token = None


def get_user_identifier(request: Request) -> str:
    """
    Rate limiter key function that scopes limits per-form (project) and per-user/ip.
    Priority:
      1. If request has a Bearer token and we can decode it, use user id.
      2. Otherwise, fallback to request.state.user if present.
      3. Otherwise, use remote IP.

    The returned key includes the `form_id` path param when available, producing
    keys like `form:{form_id}:user:{user_id}` or `form:{form_id}:ip:{ip}`.
    """
    # Determine form id from path params or query params
    form_id = None
    try:
        form_id = request.path_params.get('form_id')
    except Exception:
        form_id = None
    if not form_id:
        form_id = request.query_params.get('form_id')
    if not form_id:
        form_id = 'global'

    # 1) Try to detect user id from Authorization header (Bearer token)
    auth_header = request.headers.get('authorization', '')
    if auth_header and auth_header.lower().startswith('bearer ') and decode_access_token:
        token = auth_header.split(' ', 1)[1].strip()
        try:
            payload = decode_access_token(token)
            if payload and isinstance(payload, dict):
                user_id = payload.get('sub') or payload.get('user_id')
                if user_id:
                    return f"form:{form_id}:user:{user_id}"
        except Exception:
            pass

    # 2) Fallback to request.state.user if middleware populated it
    if hasattr(request.state, 'user') and request.state.user:
        try:
            return f"form:{form_id}:user:{request.state.user.id}"
        except Exception:
            pass

    # 3) Use IP address for anonymous requests
    ip = get_remote_address(request)
    return f"form:{form_id}:ip:{ip}"


def submission_rate_limit_selector(request: Request, state: Optional[object] = None) -> str:
    """Return per-request rate limit, handling optional state arg from SlowAPI."""
    auth_header = request.headers.get('authorization')
    return settings.RATE_LIMIT_AUTHENTICATED if auth_header else settings.RATE_LIMIT

# Default rate limits from settings
limiter = Limiter(key_func=get_user_identifier, default_limits=[settings.RATE_LIMIT])

