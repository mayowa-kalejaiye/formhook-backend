"""
App configuration and settings loader.
Loads environment variables using python-dotenv.
"""
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import List
load_dotenv()



class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/formhook")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecret")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "notifications@formhookapp.com")
    # ALLOWED_ORIGINS can be a comma-separated list (e.g. "https://app.example.com,https://admin.example.com")
    # If not set, defaults to ["*"] to allow any origin (useful for local dev).
    _raw_allowed = os.getenv("ALLOWED_ORIGINS", "*")
    ALLOWED_ORIGINS: List[str] = [o.strip() for o in _raw_allowed.split(",")] if _raw_allowed else ["*"]
    _admin_emails_raw: str = os.getenv("ADMIN_EMAILS", "")

    @property
    def admin_emails(self) -> List[str]:
        if not hasattr(self, "_admin_emails_cache"):
            emails = [email.strip() for email in self._admin_emails_raw.split(",") if email.strip()]
            self._admin_emails_cache = emails
        return self._admin_emails_cache
    
    # Rate Limiting
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "100/minute")  # Default rate limit
    RATE_LIMIT_AUTHENTICATED: str = os.getenv("RATE_LIMIT_AUTHENTICATED", "200/minute")  # Higher limit for authenticated users
    
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://formhookapp.com")

    # Submission limits
    SUBMISSION_MAX_FIELDS: int = int(os.getenv("SUBMISSION_MAX_FIELDS", "200"))
    SUBMISSION_MAX_SIZE_BYTES: int = int(os.getenv("SUBMISSION_MAX_SIZE_BYTES", str(100 * 1024)))  # 100 KB default
    
    # VAPID Keys for Push Notifications
    VAPID_PUBLIC_KEY: str = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY: str = os.getenv("VAPID_PRIVATE_KEY", "")
    VAPID_SUBJECT: str = os.getenv("VAPID_SUBJECT", "mailto:admin@formhook.com")

    ENABLE_TRIAL_REMINDER_TASK: bool = os.getenv("ENABLE_TRIAL_REMINDER_TASK", "true").lower() not in {"false", "0", "no"}
    TRIAL_REMINDER_INTERVAL_MINUTES: int = int(os.getenv("TRIAL_REMINDER_INTERVAL_MINUTES", "60"))
    REQUIRE_EMAIL_VERIFICATION: bool = os.getenv("REQUIRE_EMAIL_VERIFICATION", "true").lower() not in {"false", "0", "no"}
    RESEND_MIN_INTERVAL_SECONDS: float = float(os.getenv("RESEND_MIN_INTERVAL_SECONDS", "0.6"))

settings = Settings()
