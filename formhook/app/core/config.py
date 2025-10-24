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
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "")
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",") if "," in os.getenv("ALLOWED_ORIGINS", "*") else ["*"]
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "10/minute")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://formhook-frontend.vercel.app")
    
    # VAPID Keys for Push Notifications
    VAPID_PUBLIC_KEY: str = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY: str = os.getenv("VAPID_PRIVATE_KEY", "")
    VAPID_SUBJECT: str = os.getenv("VAPID_SUBJECT", "mailto:admin@formhook.com")

settings = Settings()
