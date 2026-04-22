#!/usr/bin/env python3
"""
Automated regression test for authentication rate limits.

This script verifies that:
1. /auth/reset-password-request enforces 3/minute (4th request -> 429).
2. /auth/login enforces 10/minute (11th request -> 429).
3. /auth/signup enforces 5/minute (6th request -> 429).
4. /auth/token enforces 10/minute (11th request -> 429).
5. /auth/email-login enforces 10/minute (11th request -> 429).
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

from formhook.app.core.config import settings
from formhook.app.core.database import Base
from formhook.app.extensions import limiter
from formhook.app.models.auth_security_counter import AuthSecurityCounter
from formhook.app.models import email_log  # noqa: F401
from formhook.app.models import form  # noqa: F401
from formhook.app.models import idempotency  # noqa: F401
from formhook.app.models import notification  # noqa: F401
from formhook.app.models.password_reset import PasswordReset  # noqa: F401
from formhook.app.models import push_subscription  # noqa: F401
from formhook.app.models import submission  # noqa: F401
from formhook.app.models.verification import EmailVerification
from formhook.app.models.user import User
from formhook.app.models import verification  # noqa: F401
from formhook.app.models import webhook_delivery  # noqa: F401
from formhook.app.routes import auth


def assert_rate_limited_response(response, endpoint: str) -> None:
    assert response.status_code == 429, f"Expected rate limit 429 for {endpoint}, got {response.status_code}"
    body = response.json()
    assert body.get("detail") == "Rate limit exceeded. Please try again later.", (
        f"Unexpected 429 detail for {endpoint}: {body}"
    )
    assert response.headers.get("Retry-After") == "60", (
        f"Expected Retry-After=60 for {endpoint}, got {response.headers.get('Retry-After')}"
    )


def run_test() -> None:
    original_require_email_verification = settings.REQUIRE_EMAIL_VERIFICATION
    settings.REQUIRE_EMAIL_VERIFICATION = False

    temp_db = tempfile.NamedTemporaryFile(prefix="formhook-auth-limit-", suffix=".db", delete=False)
    temp_db.close()

    db_path = temp_db.name
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(
        bind=engine,
        tables=[User.__table__, EmailVerification.__table__, AuthSecurityCounter.__table__],
    )

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
        reset_limited_response = None

        for _ in range(4):
            response = client.post(f"{reset_endpoint}?form_id=rl-reset", json=reset_payload)
            reset_statuses.append(response.status_code)
            reset_limited_response = response

        assert reset_statuses[:3] == [200, 200, 200], (
            f"Expected first 3 reset requests to pass, got {reset_statuses[:3]}"
        )
        assert reset_statuses[3] == 429, (
            f"Expected 4th reset request to be rate limited, got {reset_statuses[3]}"
        )
        assert_rate_limited_response(reset_limited_response, reset_endpoint)

        login_endpoint = "/auth/login"
        login_payload = {"email": "nonexistent@example.com", "password": "WrongPassword123!"}
        login_statuses = []
        login_limited_response = None

        for _ in range(11):
            response = client.post(f"{login_endpoint}?form_id=rl-login", json=login_payload)
            login_statuses.append(response.status_code)
            login_limited_response = response

        assert login_statuses[:10] == [401] * 10, (
            f"Expected first 10 login attempts to return 401, got {login_statuses[:10]}"
        )
        assert login_statuses[10] == 429, (
            f"Expected 11th login attempt to be rate limited, got {login_statuses[10]}"
        )
        assert_rate_limited_response(login_limited_response, login_endpoint)

        signup_endpoint = "/auth/signup"
        signup_statuses = []
        signup_limited_response = None

        for i in range(6):
            signup_payload = {
                "email": f"rate-limit-signup-{i}@example.com",
                "password": "StrongPassword123!",
            }
            response = client.post(f"{signup_endpoint}?form_id=rl-signup", json=signup_payload)
            signup_statuses.append(response.status_code)
            signup_limited_response = response

        assert signup_statuses[:5] == [200] * 5, (
            f"Expected first 5 signup requests to pass, got {signup_statuses[:5]}"
        )
        assert signup_statuses[5] == 429, (
            f"Expected 6th signup request to be rate limited, got {signup_statuses[5]}"
        )
        assert_rate_limited_response(signup_limited_response, signup_endpoint)

        token_endpoint = "/auth/token"
        token_statuses = []
        token_limited_response = None

        for _ in range(11):
            response = client.post(
                f"{token_endpoint}?form_id=rl-token",
                data={"username": "nonexistent@example.com", "password": "WrongPassword123!"},
            )
            token_statuses.append(response.status_code)
            token_limited_response = response

        assert token_statuses[:10] == [401] * 10, (
            f"Expected first 10 token requests to return 401, got {token_statuses[:10]}"
        )
        assert token_statuses[10] == 429, (
            f"Expected 11th token request to be rate limited, got {token_statuses[10]}"
        )
        assert_rate_limited_response(token_limited_response, token_endpoint)

        email_login_endpoint = "/auth/email-login"
        email_login_payload = {"email": "nonexistent@example.com", "password": "WrongPassword123!"}
        email_login_statuses = []
        email_login_limited_response = None

        for _ in range(11):
            response = client.post(f"{email_login_endpoint}?form_id=rl-email-login", json=email_login_payload)
            email_login_statuses.append(response.status_code)
            email_login_limited_response = response

        assert email_login_statuses[:10] == [401] * 10, (
            f"Expected first 10 email-login attempts to return 401, got {email_login_statuses[:10]}"
        )
        assert email_login_statuses[10] == 429, (
            f"Expected 11th email-login attempt to be rate limited, got {email_login_statuses[10]}"
        )
        assert_rate_limited_response(email_login_limited_response, email_login_endpoint)

        print("PASS: /auth/reset-password-request enforces 3/minute (4th -> 429).")
        print("PASS: /auth/login enforces 10/minute (11th -> 429).")
        print("PASS: /auth/signup enforces 5/minute (6th -> 429).")
        print("PASS: /auth/token enforces 10/minute (11th -> 429).")
        print("PASS: /auth/email-login enforces 10/minute (11th -> 429).")
    finally:
        settings.REQUIRE_EMAIL_VERIFICATION = original_require_email_verification
        Base.metadata.drop_all(
            bind=engine,
            tables=[AuthSecurityCounter.__table__, EmailVerification.__table__, User.__table__],
        )
        engine.dispose()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    run_test()
