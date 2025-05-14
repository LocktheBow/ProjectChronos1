"""
api.deps
========

FastAPI dependency providers.

`get_portfolio` now returns a fresh **DBPortfolioManager** so every
request talks to the persistent SQLite store instead of the in‑memory
PortfolioManager.

Also includes dependencies for external API clients like OpenCorporates, Data Axle, and SEC EDGAR.
"""

from functools import lru_cache
from typing import AsyncGenerator, Dict

from fastapi import Depends
from httpx import AsyncClient

from chronos.portfolio_db import DBPortfolioManager
from chronos.relationships import RelationshipGraph
from chronos.settings import settings
from chronos.scrapers.opencorp import OpenCorporatesScraper
from chronos.scrapers.cobalt import CobaltScraper


@lru_cache
def get_portfolio() -> DBPortfolioManager:
    """Singleton DB‑backed portfolio manager (persists across requests)."""
    return DBPortfolioManager()


@lru_cache
def get_relationships() -> RelationshipGraph:
    """Singleton relationship graph (persists across requests)."""
    return RelationshipGraph()


@lru_cache
def get_settings():
    """Return application settings."""
    return settings


@lru_cache
def get_opencorp_scraper():
    """Return a configured OpenCorporates scraper."""
    return OpenCorporatesScraper(api_token=settings.opencorp_api_token)


@lru_cache
def get_cobalt_scraper():
    """Return a configured Cobalt Intelligence scraper."""
    return CobaltScraper(api_key=settings.cobalt_api_key)


async def get_data_axle(settings=Depends(get_settings)) -> AsyncGenerator[AsyncClient, None]:
    """
    Return an AsyncClient configured for Data Axle API access.
    
    Args:
        settings: Application settings with Data Axle credentials
        
    Yields:
        AsyncClient: Configured HTTP client for Data Axle API
    """
    async with AsyncClient(
        base_url=str(settings.data_axle_base),
        headers={
            # X-AUTH-TOKEN is the standard header for Data Axle API
            "X-AUTH-TOKEN": settings.data_axle_key,
            # For backward compatibility, also include x-api-key
            "x-api-key": settings.data_axle_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"{settings.sec_ua_app} ({settings.sec_ua_email})",  # polite UA
            # Additional headers that might be needed for Data Axle API
            "Cache-Control": "no-cache"
        },
        timeout=30.0  # Increased timeout for API requests
    ) as client:
        yield client


def edgar_headers(settings=Depends(get_settings)) -> Dict[str, str]:
    """
    Return headers required for SEC EDGAR API access.
    
    Args:
        settings: Application settings with SEC EDGAR credentials
        
    Returns:
        Dict[str, str]: Headers for SEC EDGAR API
    """
    ua = f"{settings.sec_ua_app} (+{settings.sec_ua_email})"
    return {
        "User-Agent": ua, 
        "Accept-Encoding": "gzip, deflate", 
        "Host": "www.sec.gov"
    }


async def get_edgar_client(
    headers=Depends(edgar_headers),
    settings=Depends(get_settings)
) -> AsyncGenerator[AsyncClient, None]:
    """
    Return an AsyncClient configured for SEC EDGAR API access.
    
    Args:
        headers: Headers for SEC EDGAR API
        settings: Application settings
        
    Yields:
        AsyncClient: Configured HTTP client for SEC EDGAR API
    """
    async with AsyncClient(
        base_url=str(settings.sec_edgar_base),
        headers=headers,
        timeout=30.0  # SEC API can be slow
    ) as client:
        yield client