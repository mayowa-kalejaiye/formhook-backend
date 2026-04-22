#!/usr/bin/env python3
"""
Automated regression test for authentication rate limits.

This script verifies that:
1. /auth/reset-password-request enforces 3/minute (4th request -> 429).
2. /auth/login enforces 10/minute (11th request -> 429).
"""

import os
import tempfile

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from formhook.app.core.database import Base
from formhook.app.extensions import limiter
from formhook.app.models import email_log  # noqa: F401
from formhook.app.models import form  # noqa: F401
from formhook.app.models import idempotency  # noqa: F401
from formhook.app.models import notification  # noqa: F401
from formhook.app.models.password_reset import PasswordReset  # noqa: F401
from formhook.app.models import push_subscription  # noqa: F401
from formhook.app.models import submission  # noqa: F401
from formhook.app.models.user import User
from formhook.app.models import verification  # noqa: F401
from formhook.app.models import webhook_delivery  # noqa: F401
from formhook.app.routes import auth


def run_test() -> None:
    temp_db = tempfile.NamedTemporaryFile(prefix="formhook-auth-limit-", suffix=".db", delete=False)
    temp_db.close()

    db_path = temp_db.name
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine, tables=[User.__table__])

    def test_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI(title="Auth Rate Limit Regression")
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please try again later."},
            headers={"Retry-After": "60"},
        )

    app.add_middleware(SlowAPIMiddleware)
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])
    app.dependency_overrides[auth.get_db] = test_get_db

    try:
        client = TestClient(app)

        reset_endpoint = "/auth/reset-password-request"
        reset_payload = {"email": "nonexistent@example.com"}
        reset_statuses = []

        for _ in range(4):
            response = client.post(reset_endpoint, json=reset_payload)
            reset_statuses.append(response.status_code)

        assert reset_statuses[:3] == [200, 200, 200], (
            f"Expected first 3 reset requests to pass, got {reset_statuses[:3]}"
        )
        assert reset_statuses[3] == 429, (
            f"Expected 4th reset request to be rate limited, got {reset_statuses[3]}"
        )

        login_endpoint = "/auth/login"
        login_payload = {"email": "nonexistent@example.com", "password": "WrongPassword123!"}
        login_statuses = []

        for _ in range(11):
            response = client.post(login_endpoint, json=login_payload)
            login_statuses.append(response.status_code)

        assert login_statuses[:10] == [401] * 10, (
            f"Expected first 10 login attempts to return 401, got {login_statuses[:10]}"
        )
        assert login_statuses[10] == 429, (
            f"Expected 11th login attempt to be rate limited, got {login_statuses[10]}"
        )

        print("PASS: /auth/reset-password-request enforces 3/minute (4th -> 429).")
        print("PASS: /auth/login enforces 10/minute (11th -> 429).")
    finally:
        Base.metadata.drop_all(bind=engine, tables=[User.__table__])
        engine.dispose()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    run_test()
