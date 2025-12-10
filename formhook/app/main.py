"""
FormHook FastAPI Application Entry Point
----------------------------------------
This is the main entry point for the FormHook backend service.
It includes app setup, middleware, and route registration.
"""
import asyncio
from contextlib import suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from .core.config import settings
from .routes import auth, forms, submissions, dashboard, analytics, subscription, notifications, push_notifications
from .tasks.trial_reminder_scheduler import run_trial_reminder_loop

app = FastAPI(title="FormHook API", description="Plug-and-play backend for HTML forms.")

# CORS Middleware - Update to explicitly allow the frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [settings.FRONTEND_URL,
         "https://formhook-frontend.vercel.app",
         "https://formhookapp.com",
         "http://localhost:3000"] +
        (settings.ALLOWED_ORIGINS if isinstance(settings.ALLOWED_ORIGINS, list) else [])
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Rate limiting middleware (SlowAPI)

from .extensions import limiter
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from fastapi.requests import Request

app.state.limiter = limiter
app.state.trial_reminder_task = None
app.state.trial_reminder_stop = None

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    # Include a Retry-After header to help clients back off; default to 60s
    headers = {"Retry-After": "60"}
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
        headers=headers
    )

from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)


@app.on_event("startup")
async def start_background_tasks() -> None:
    if not settings.ENABLE_TRIAL_REMINDER_TASK:
        return
    stop_event = asyncio.Event()
    app.state.trial_reminder_stop = stop_event
    app.state.trial_reminder_task = asyncio.create_task(run_trial_reminder_loop(stop_event))


@app.on_event("shutdown")
async def stop_background_tasks() -> None:
    task = getattr(app.state, "trial_reminder_task", None)
    stop_event = getattr(app.state, "trial_reminder_stop", None)
    if stop_event:
        stop_event.set()
    if task:
        with suppress(asyncio.CancelledError):
            await task

# Register routes
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(forms.router, prefix="/forms", tags=["Forms"])
app.include_router(submissions.router, prefix="/forms", tags=["Submissions"])
app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(analytics.router, tags=["Forms"])
app.include_router(subscription.router, prefix="/subscription", tags=["Subscription"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
app.include_router(push_notifications.router, prefix="/notifications/push", tags=["Push Notifications"])


# Root endpoint
@app.get("/")
def read_root():
    """Root endpoint."""
    return {"message": "Welcome to FormHook!"}

# Health check endpoint for deployment
@app.get("/health")
def health_check():
    """Health check endpoint for deployment platforms."""
    return {"status": "ok"}

# Email verification redirect endpoint
@app.get("/verify-email")
async def redirect_to_frontend(token: str):
    """Redirects email verification links to the frontend verification page"""
    frontend_url = settings.FRONTEND_URL
    redirect_url = f"{frontend_url}/verify-email?token={token}"
    return RedirectResponse(url=redirect_url)
