#!/usr/bin/env python3
"""
Automated regression test for password-reset session revocation.

This script verifies that:
1. A JWT issued before password reset is rejected after reset.
2. A JWT issued after password reset is accepted.
"""

import os
import tempfile

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from formhook.app.core.database import Base
from formhook.app.core.security import create_access_token, hash_password, verify_password
from formhook.app.dependencies import get_current_user
from formhook.app.models import email_log  # noqa: F401
from formhook.app.models import form  # noqa: F401
from formhook.app.models import idempotency  # noqa: F401
from formhook.app.models import notification  # noqa: F401
from formhook.app.models.password_reset import PasswordReset
from formhook.app.models import push_subscription  # noqa: F401
from formhook.app.models import submission  # noqa: F401
from formhook.app.models.user import User
from formhook.app.models import verification  # noqa: F401
from formhook.app.models import webhook_delivery  # noqa: F401
from formhook.app.routes.auth import build_auth_token_payload
from formhook.app.services.password_reset import create_password_reset_token, reset_password


def run_test() -> None:
    temp_db = tempfile.NamedTemporaryFile(prefix="formhook-token-revocation-", suffix=".db", delete=False)
    temp_db.close()

    db_path = temp_db.name
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    try:
        Base.metadata.create_all(bind=engine, tables=[User.__table__, PasswordReset.__table__])

        db = SessionLocal()
        try:
            user = User(
                email="revocation-test@example.com",
                password_hash=hash_password("OldPassword123!"),
                is_verified=True,
                token_version=0,
                subscription_status="active",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            old_token = create_access_token(build_auth_token_payload(user))

            reset_token = create_password_reset_token(db, user.id)
            reset_ok = reset_password(db, reset_token, "NewPassword123!")
            assert reset_ok, "Expected password reset to succeed"

            db.refresh(user)
            assert user.token_version == 1, "Expected token_version to increment after password reset"
            assert verify_password("NewPassword123!", user.password_hash), "Expected new password to be stored"
            assert not verify_password("OldPassword123!", user.password_hash), "Expected old password to be invalid"

            try:
                get_current_user(old_token, db)
                raise AssertionError("Old token should have been rejected after password reset")
            except HTTPException as exc:
                assert exc.status_code == 401, f"Expected 401 for revoked token, got {exc.status_code}"
                assert "revoked" in (exc.detail or "").lower(), "Expected revoked-session detail message"

            new_token = create_access_token(build_auth_token_payload(user))
            current_user = get_current_user(new_token, db)
            assert current_user.id == user.id, "Expected new token to authenticate the same user"

            print("PASS: Password reset revokes old JWT sessions and keeps new JWT sessions valid.")
        finally:
            db.close()
    finally:
        Base.metadata.drop_all(bind=engine, tables=[PasswordReset.__table__, User.__table__])
        engine.dispose()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    run_test()
