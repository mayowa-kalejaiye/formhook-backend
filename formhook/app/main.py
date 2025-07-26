"""
FormHook FastAPI Application Entry Point
----------------------------------------
This is the main entry point for the FormHook backend service.
It includes app setup, middleware, and route registration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .routes import auth, forms, submissions, dashboard

app = FastAPI(title="FormHook API", description="Plug-and-play backend for HTML forms.")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiting middleware (SlowAPI)

from .extensions import limiter
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from fastapi.requests import Request

app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )

from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)

# Register routes
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(forms.router, prefix="/forms", tags=["Forms"])
app.include_router(submissions.router, prefix="/forms", tags=["Submissions"])
app.include_router(dashboard.router, tags=["Dashboard"])

# Root endpoint
@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"message": "Welcome to FormHook!"}
