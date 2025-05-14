"""
chronos.scrapers.edgar
=====================

SEC EDGAR API integration for enriching corporate entity data with SEC filings.

This module provides functionality to look up companies in the SEC EDGAR database,
find their CIK numbers, and retrieve information about their latest filings.

The EDGAR integration is optional and can be enabled/disabled via configuration.

This version uses the new SEC EDGAR Search API v2 endpoints and async HTTP clients.

Usage:
------
edgar = EdgarClient(client)  # client is an httpx.AsyncClient
filing_info = await edgar.enrich_entity(entity)  # Adds SEC info to entity.notes
"""

from __future__ import annotations

import os
import re
import json
import logging
import sqlite3
import time
import asyncio
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, cast

from httpx import AsyncClient, Response

from chronos.models import CorporateEntity

# Configure logging
logger = logging.getLogger(__name__)

# Cache setup
CACHE_DB_PATH = Path(os.environ.get("CHRONOS_CACHE_DIR", ".")) / "chronos_cache.db"
CACHE_DURATION = timedelta(hours=24)

# Common SEC form types of interest
FORM_TYPES = ['10-K', '10-Q', '8-K', 'S-1', 'S-3', 'S-4', '13F']


class EdgarClient:
    """
    Client for interacting with the SEC EDGAR Search API v2.
    
    Provides functionality to search for companies, retrieve CIK numbers,
    and get information about recent filings.
    """
    
    def __init__(self, client: AsyncClient, use_cache: bool = True, enabled: bool = True):
        """
        Initialize the EDGAR client.
        
        Args:
            client: AsyncClient configured with SEC EDGAR API headers
            use_cache: Whether to cache API responses (defaults to True)
            enabled: Whether the EDGAR integration is enabled
        """
        self.client = client
        self.use_cache = use_cache
        self.enabled = enabled
        self._cik_cache: Dict[str, str] = {}  # In-memory CIK lookup cache
        
        # Setup database cache if needed
        if self.use_cache:
            self._setup_cache_if_needed()
        
    def _setup_cache_if_needed(self) -> None:
        """Create the cache database and tables if they don't exist."""
        if not CACHE_DB_PATH.parent.exists():
            CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()
        
        # Create cache table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS edgar_cache (
            query TEXT,
            response TEXT,
            timestamp TIMESTAMP,
            PRIMARY KEY (query)
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def _get_cached_response(self, query: str) -> Optional[Dict]:
        """
        Retrieve a cached response if it exists and is not expired.
        
        Args:
            query: The search query or CIK
            
        Returns:
            The cached response as a dict, or None if not found or expired
        """
        if not self.use_cache:
            return None
            
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT response, timestamp FROM edgar_cache
        WHERE query = ?
        ''', (query,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
            
        response_str, timestamp_str = result
        timestamp = datetime.fromisoformat(timestamp_str)
        
        # Check if cache entry is expired
        if datetime.now() - timestamp > CACHE_DURATION:
            return None
            
        return json.loads(response_str)
        
    def _cache_response(self, query: str, response: Dict) -> None:
        """
        Cache an API response.
        
        Args:
            query: The search query or CIK
            response: The API response to cache
        """
        if not self.use_cache:
            return
            
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()
        
        # Store with current timestamp
        timestamp = datetime.now().isoformat()
        response_str = json.dumps(response)
        
        cursor.execute('''
        INSERT OR REPLACE INTO edgar_cache
        (query, response, timestamp)
        VALUES (?, ?, ?)
        ''', (query, response_str, timestamp))
        
        conn.commit()
        conn.close()
        
    async def search_companies(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for companies by name using the SEC EDGAR Search API.
        
        Args:
            query: Company name or keyword to search for
            limit: Maximum number of results to return
            
        Returns:
            List of company information dictionaries
        """
        if not self.enabled:
            logger.info("EDGAR integration is disabled")
            return []
            
        # Check cache first
        cache_key = f"edgar_search_{query}_{limit}"
        cached = self._get_cached_response(cache_key)
        
        if cached:
            logger.info(f"Using cached EDGAR search results for '{query}'")
            return cached.get("hits", {}).get("hits", [])
            
        # Add delay to respect SEC rate limits (10 req/sec)
        await self._respect_rate_limit()
        
        params = {
            "keys": query,
            "limit": str(limit)
        }
        
        try:
            response = await self.client.get("/search-index", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Cache the response
            self._cache_response(cache_key, data)
            
            # Extract company information from the response
            results = []
            if "hits" in data and "hits" in data["hits"]:
                for hit in data["hits"]["hits"][:limit]:
                    if "_source" in hit:
                        results.append(hit["_source"])
            
            return results
        
        except Exception as e:
            logger.error(f"Error searching companies in EDGAR API: {e}")
            return []
    
    async def get_company_filings(
        self, 
        cik: str, 
        form_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get company filings by CIK and optional form types.
        
        Args:
            cik: Company CIK number (with or without leading zeros)
            form_types: Optional list of form types to filter by (e.g., ["10-K", "10-Q"])
            limit: Maximum number of results to return
            
        Returns:
            List of filing information dictionaries
        """
        if not self.enabled:
            logger.info("EDGAR integration is disabled")
            return []
            
        # Normalize CIK by removing leading zeros
        cik_normalized = cik.strip("0")
        if not cik_normalized.isdigit():
            logger.error(f"Invalid CIK format: {cik}")
            return []
        
        # Check cache first
        cache_key = f"v2_filings_{cik_normalized}_{'-'.join(form_types or [])}_{limit}"
        cached = self._get_cached_response(cache_key)
        
        if cached:
            logger.info(f"Using cached EDGAR filings for CIK '{cik_normalized}'")
            return cached.get("data", {}).get("hits", [])
        
        # Add delay to respect SEC rate limits (10 req/sec)
        await self._respect_rate_limit()
        
        params: Dict[str, Any] = {
            "ciks": cik_normalized,
            "limit": str(limit)
        }
        
        if form_types:
            params["forms"] = ",".join(form_types)
        
        try:
            response = await self.client.get("/filings", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Cache the response
            self._cache_response(cache_key, data)
            
            return data.get("data", {}).get("hits", [])
        
        except Exception as e:
            logger.error(f"Error getting company filings from EDGAR API v2: {e}")
            return []
    
    async def get_company_cik(self, company_name: str) -> Optional[str]:
        """
        Get a company's CIK by name.
        
        Args:
            company_name: Company name to search for
            
        Returns:
            CIK number if found, None otherwise
        """
        if not self.enabled:
            logger.info("EDGAR integration is disabled")
            return None
            
        # Check in-memory cache first
        if company_name.lower() in self._cik_cache:
            return self._cik_cache[company_name.lower()]
        
        # Search for the company
        companies = await self.search_companies(company_name, limit=1)
        if not companies:
            logger.info(f"No company found in EDGAR for '{company_name}'")
            return None
        
        # Extract CIK from the first match
        cik = companies[0].get("cik")
        if cik:
            # Cache for future lookups
            self._cik_cache[company_name.lower()] = cik
            return cik
        
        return None
    
    async def enrich_entity(self, entity: CorporateEntity) -> CorporateEntity:
        """
        Enrich a CorporateEntity with SEC EDGAR data.
        
        Args:
            entity: CorporateEntity to enrich
            
        Returns:
            Enriched CorporateEntity with SEC data
        """
        if not self.enabled:
            logger.info("EDGAR integration is disabled")
            return entity
            
        logger.info(f"Enriching entity {entity.name} with SEC EDGAR data")
        
        try:
            # Get company CIK
            cik = await self.get_company_cik(entity.name)
            if not cik:
                logger.info(f"No CIK found for '{entity.name}'")
                return entity
            
            # Store CIK in entity metadata
            if not hasattr(entity, "metadata"):
                entity.metadata = {}
            entity.metadata["sec_cik"] = cik
            
            # Get recent filings
            filings = await self.get_company_filings(cik, form_types=["10-K", "10-Q", "8-K"], limit=5)
            
            # Add SEC information to entity notes
            sec_notes = [f"SEC CIK: {cik}"]
            
            if filings:
                sec_notes.append("\nLatest SEC Filings:")
                for filing in filings:
                    form_type = filing.get("form", "Unknown")
                    filing_date = filing.get("filingDate", "Unknown")
                    filing_url = filing.get("fileUrl", "")
                    
                    sec_notes.append(f"- {form_type} ({filing_date}): {filing_url}")
            
            # Update entity notes
            if entity.notes:
                entity.notes += "\n\n" + "\n".join(sec_notes)
            else:
                entity.notes = "\n".join(sec_notes)
            
            return entity
            
        except Exception as e:
            logger.error(f"Error enriching entity with SEC data: {e}")
            return entity
    
    async def _respect_rate_limit(self):
        """Add a small delay to respect SEC's rate limit of 10 req/s."""
        await asyncio.sleep(0.1)