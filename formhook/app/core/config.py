"""
App configuration and settings loader.
Loads environment variables using python-dotenv.
"""
import os
from dotenv import load_dotenv
from pydantic import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/formhook")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecret")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "")
    ALLOWED_ORIGINS: list = [os.getenv("ALLOWED_ORIGINS", "*")]
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "10/minute")

settings = Settings()
