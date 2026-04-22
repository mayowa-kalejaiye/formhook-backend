#!/usr/bin/env python3
"""
Quick smoke test for the password reset flow.

This script is intentionally interactive because the reset token is delivered
by email. It will:
1. Request a password reset email for the entered address.
2. Prompt you to paste the reset token from the email.
3. Submit the new password to the backend.

Set BASE_URL to your running backend before executing.
"""

from getpass import getpass

import requests

BASE_URL = "http://localhost:8000"


def request_reset(email: str) -> None:
    response = requests.post(f"{BASE_URL}/auth/reset-password-request", json={"email": email})
    print(f"Request reset status: {response.status_code}")
    try:
        print(response.json())
    except Exception:
        print(response.text)


def confirm_reset(token: str, password: str) -> None:
    response = requests.post(
        f"{BASE_URL}/auth/reset-password",
        json={"token": token, "password": password},
    )
    print(f"Confirm reset status: {response.status_code}")
    try:
        print(response.json())
    except Exception:
        print(response.text)


def main() -> None:
    print("FormHook Password Reset Smoke Test")
    print("=" * 40)
    print(f"Backend URL: {BASE_URL}")

    email = input("Email address: ").strip()
    if not email:
        print("Email is required.")
        return

    request_reset(email)

    print("\nCheck the inbox for the reset email and paste the token from the link below:")
    token = input("Reset token: ").strip()
    if not token:
        print("Reset token is required.")
        return

    password = getpass("New password: ").strip()
    if not password:
        print("New password is required.")
        return

    confirm = getpass("Confirm new password: ").strip()
    if password != confirm:
        print("Passwords do not match.")
        return

    confirm_reset(token, password)
    print("\nSmoke test complete.")


if __name__ == "__main__":
    main()
