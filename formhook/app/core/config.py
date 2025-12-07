"""
App configuration and settings loader.
Loads environment variables using python-dotenv.
"""
import os
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from typing import List, Union
load_dotenv()



class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/formhook")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecret")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "")
    # ALLOWED_ORIGINS can be a comma-separated list (e.g. "https://app.example.com,https://admin.example.com")
    # If not set, defaults to ["*"] to allow any origin (useful for local dev).
    _raw_allowed = os.getenv("ALLOWED_ORIGINS", "*")
    ALLOWED_ORIGINS: List[str] = [o.strip() for o in _raw_allowed.split(",")] if _raw_allowed else ["*"]
    ADMIN_EMAILS: List[str] = Field(default_factory=list)

    @field_validator("ADMIN_EMAILS", mode="before")
    @classmethod
    def _parse_admin_emails(cls, value: Union[str, List[str], None]):
        if value is None:
            return []
        if isinstance(value, list):
            return [email.strip() for email in value if isinstance(email, str) and email.strip()]
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            return [email.strip() for email in value.split(",") if email.strip()]
        raise ValueError("ADMIN_EMAILS must be a comma-separated string or list of strings")
    
    # Rate Limiting
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "100/minute")  # Default rate limit
    RATE_LIMIT_AUTHENTICATED: str = os.getenv("RATE_LIMIT_AUTHENTICATED", "200/minute")  # Higher limit for authenticated users
    
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://formhook-frontend.vercel.app")

    # Submission limits
    SUBMISSION_MAX_FIELDS: int = int(os.getenv("SUBMISSION_MAX_FIELDS", "200"))
    SUBMISSION_MAX_SIZE_BYTES: int = int(os.getenv("SUBMISSION_MAX_SIZE_BYTES", str(100 * 1024)))  # 100 KB default
    
    # VAPID Keys for Push Notifications
    VAPID_PUBLIC_KEY: str = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY: str = os.getenv("VAPID_PRIVATE_KEY", "")
    VAPID_SUBJECT: str = os.getenv("VAPID_SUBJECT", "mailto:admin@formhook.com")

settings = Settings()
