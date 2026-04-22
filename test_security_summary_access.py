#!/usr/bin/env python3
"""
Automated regression test for admin-only security summary access.

This script verifies that:
1. Non-admin users receive 403 for GET /dashboard/security-summary.
2. Admin users receive 200 for GET /dashboard/security-summary.
"""

import os
import tempfile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from formhook.app import dependencies
from formhook.app.core.database import Base
from formhook.app.core.security import create_access_token, hash_password

# Preload relationship targets for SQLAlchemy mapper configuration.
from formhook.app.models import email_log  # noqa: F401
from formhook.app.models import form  # noqa: F401
from formhook.app.models.auth_security_counter import AuthSecurityCounter
from formhook.app.models import idempotency  # noqa: F401
from formhook.app.models import notification  # noqa: F401
from formhook.app.models.password_reset import PasswordReset  # noqa: F401
from formhook.app.models import push_subscription  # noqa: F401
from formhook.app.models import submission  # noqa: F401
from formhook.app.models.user import User
from formhook.app.models.verification import EmailVerification  # noqa: F401
from formhook.app.models import webhook_delivery  # noqa: F401
from formhook.app.routes import dashboard


def make_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "token_version": int(getattr(user, "token_version", 0) or 0),
    }
    return create_access_token(payload)


def run_test() -> None:
    temp_db = tempfile.NamedTemporaryFile(prefix="formhook-security-summary-", suffix=".db", delete=False)
    temp_db.close()

    db_path = temp_db.name
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine, tables=[User.__table__, AuthSecurityCounter.__table__])

    def test_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI(title="Security Summary Access Regression")
    app.include_router(dashboard.router, tags=["Dashboard"])
    app.dependency_overrides[dependencies.get_db] = test_get_db

    try:
        db = SessionLocal()
        try:
            admin_user = User(
                email="admin-security@example.com",
                password_hash=hash_password("AdminPassword123!"),
                is_verified=True,
                is_admin=True,
                token_version=0,
                subscription_status="active",
            )
            non_admin_user = User(
                email="user-security@example.com",
                password_hash=hash_password("UserPassword123!"),
                is_verified=True,
                is_admin=False,
                token_version=0,
                subscription_status="active",
            )
            db.add(admin_user)
            db.add(non_admin_user)
            db.commit()
            db.refresh(admin_user)
            db.refresh(non_admin_user)

            db.add(
                AuthSecurityCounter(
                    endpoint="/auth/login",
                    email="target@example.com",
                    ip_address="127.0.0.1",
                    attempts=12,
                )
            )
            db.commit()
        finally:
            # We must not close the session before make_token() access user attributes.
            # However, for consistency we'll ensure user objects are detached but with loaded attributes
            # or simply generate the tokens while the session is still active.
            non_admin_token = make_token(non_admin_user)
            admin_token = make_token(admin_user)
            db.close()

        client = TestClient(app)

        non_admin_response = client.get(
            "/dashboard/security-summary",
            headers={"Authorization": f"Bearer {non_admin_token}"},
        )
        assert non_admin_response.status_code == 403, (
            f"Expected 403 for non-admin, got {non_admin_response.status_code}"
        )
        assert non_admin_response.json().get("detail") == "Admin access required", (
            f"Unexpected non-admin detail: {non_admin_response.json()}"
        )

        admin_token = make_token(admin_user)
        admin_response = client.get(
            "/dashboard/security-summary",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_response.status_code == 200, (
            f"Expected 200 for admin, got {admin_response.status_code}"
        )

        body = admin_response.json()
        assert "totals" in body and "endpoint_breakdown" in body and "top_signals" in body, (
            f"Unexpected admin response payload: {body}"
        )
        assert body["totals"].get("failed_auth_attempts", 0) >= 12, (
            f"Expected failed attempts >= 12, got {body['totals']}"
        )

        print("PASS: /dashboard/security-summary denies non-admin users and allows admin users.")
    finally:
        Base.metadata.drop_all(bind=engine, tables=[AuthSecurityCounter.__table__, User.__table__])
        engine.dispose()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    run_test()
