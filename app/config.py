"""
Configuration settings for AI Resume ATS System
===============================================

Centralized configuration management using environment variables
with sensible defaults for development and production environments.
"""

import os
from typing import List


class Settings:
    """Application settings with environment variable support."""

    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "false").lower() == "true"

    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    ).split(",")
    ALLOW_CREDENTIALS: bool = os.getenv("ALLOW_CREDENTIALS", "true").lower() == "true"
    ALLOWED_METHODS: List[str] = os.getenv(
        "ALLOWED_METHODS",
        "GET,POST,PUT,DELETE,OPTIONS"
    ).split(",")
    ALLOWED_HEADERS: List[str] = os.getenv(
        "ALLOWED_HEADERS",
        "Accept,Accept-Language,Content-Language,Content-Type,Authorization"
    ).split(",")

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./resume_ats.db")

    # AI/Model Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")

    # Processing Configuration
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    PROCESSING_TIMEOUT_SECONDS: int = int(os.getenv("PROCESSING_TIMEOUT_SECONDS", "30"))

    # Security Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    API_KEY_REQUIRED: bool = os.getenv("API_KEY_REQUIRED", "false").lower() == "true"

    # Rate Limiting (optional)
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW_MINUTES: int = int(os.getenv("RATE_LIMIT_WINDOW_MINUTES", "15"))


# Global settings instance
settings = Settings()