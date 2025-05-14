"""
chronos.settings
===============

Configuration settings for the Chronos application.

This module provides centralized configuration options that can be used across
the Chronos application. It includes default values that can be overridden
via environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from pydantic import HttpUrl, Field
from pydantic_settings import BaseSettings

# ---------------------------------------------------------------------------
# Base directories
# ---------------------------------------------------------------------------
# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Database settings
# ---------------------------------------------------------------------------
DB_FILE = os.environ.get("CHRONOS_DB_FILE", BASE_DIR / "chronos.db")
DB_URL = f"sqlite:///{DB_FILE}"
DB_ECHO = os.environ.get("CHRONOS_DB_ECHO", "False").lower() == "true"

# API settings
# ---------------------------------------------------------------------------
API_HOST = os.environ.get("CHRONOS_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("CHRONOS_API_PORT", "8000"))
API_WORKERS = int(os.environ.get("CHRONOS_API_WORKERS", "1"))
API_DEBUG = os.environ.get("CHRONOS_API_DEBUG", "False").lower() == "true"

# Scraper settings
# ---------------------------------------------------------------------------
SCRAPER_TIMEOUT = int(os.environ.get("CHRONOS_SCRAPER_TIMEOUT", "30"))
SCRAPER_USER_AGENT = os.environ.get(
    "CHRONOS_SCRAPER_USER_AGENT", 
    "Chronos/0.1.0 Corporate Entity Research Tool"
)

# Cache settings
# ---------------------------------------------------------------------------
CACHE_ENABLED = os.environ.get("CHRONOS_CACHE_ENABLED", "True").lower() == "true"
CACHE_TTL = int(os.environ.get("CHRONOS_CACHE_TTL", "3600"))  # 1 hour

# ---------------------------------------------------------------------------
# Pydantic settings model for API integrations
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    """Pydantic model for application settings, loaded from environment variables."""
    
    # Data Axle API settings
    data_axle_key: str = Field(default=os.environ.get("DATA_AXLE_KEY", "b22dabd68be03d0d1bd0aaad"), description="Data Axle API key")
    data_axle_base: HttpUrl = Field(
        default=os.environ.get("DATA_AXLE_BASE_URL", "https://api.data-axle.com/direct/v1"),
        description="Data Axle API base URL"
    )
    
    # SEC EDGAR API settings
    sec_ua_email: str = Field(default=os.environ.get("SEC_UA_EMAIL", "consolesuperior@gmail.com"), description="Email address for SEC API User-Agent")
    sec_ua_app: str = Field(default=os.environ.get("SEC_UA_APP", "ChronosBot/0.1"), description="App name for SEC API User-Agent")
    sec_edgar_base: HttpUrl = Field(
        default=os.environ.get("SEC_EDGAR_BASE_URL", "https://efts.sec.gov/LATEST"),
        description="SEC EDGAR API base URL"
    )
    
    # General API settings
    api_cache_ttl: int = Field(86400, description="API cache TTL in seconds (24 hours)")
    
    class Config:
        """Configuration for the settings model."""
        env_prefix = ""  # no prefix, use variable names as-is
        env_file = ".env"  # load from .env file if present
        case_sensitive = False  # case-insensitive environment variables

# Initialize settings
settings = Settings()