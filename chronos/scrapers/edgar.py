"""
chronos.scrapers.edgar
=====================

SEC EDGAR API integration for enriching corporate entity data with SEC filings.

This module provides functionality to look up companies in the SEC EDGAR database,
find their CIK numbers, and retrieve information about their latest filings.

The EDGAR integration is optional and can be enabled/disabled via configuration.

Usage:
------
edgar = EdgarClient()
filing_info = edgar.enrich_entity(entity)  # Adds SEC info to entity.notes
"""

from __future__ import annotations

import os
import re
import json
import logging
import sqlite3
import requests
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from chronos.models import CorporateEntity

# Configure logging
logger = logging.getLogger(__name__)

# API Constants
EDGAR_SEARCH_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
EDGAR_COMPANY_URL = "https://www.sec.gov/edgar/searchedgar/companysearch"
EDGAR_USER_AGENT = os.environ.get(
    "EDGAR_USER_AGENT", 
    "Chronos Corporate Entity Tracker (Educational Project)"
)
CACHE_DURATION = timedelta(hours=24)

# Common SEC form types of interest
FORM_TYPES = ['10-K', '10-Q', '8-K', 'S-1', 'S-3', 'S-4', '13F']

# Cache setup
CACHE_DB_PATH = Path(os.environ.get("CHRONOS_CACHE_DIR", ".")) / "chronos_cache.db"


class EdgarClient:
    """
    Client for interacting with the SEC EDGAR database.
    
    Provides functionality to search for companies, retrieve CIK numbers,
    and get information about recent filings.
    """
    
    def __init__(self, use_cache: bool = True, enabled: bool = True):
        """
        Initialize the EDGAR client.
        
        Args:
            use_cache: Whether to cache API responses (defaults to True)
            enabled: Whether the EDGAR integration is enabled
        """
        self.use_cache = use_cache
        self.enabled = enabled
        self._setup_cache_if_needed()
        
    def _setup_cache_if_needed(self) -> None:
        """Create the cache database and tables if they don't exist."""
        if not self.use_cache:
            return
            
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
        
    def _make_api_request(self, url: str, params: Dict) -> Dict:
        """
        Make a request to the SEC EDGAR API.
        
        Args:
            url: API endpoint URL
            params: Query parameters
            
        Returns:
            Response data as a dictionary
            
        Raises:
            ValueError: For API errors or invalid responses
        """
        headers = {
            "User-Agent": EDGAR_USER_AGENT,
            "Accept": "application/json",
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            # Check if response is JSON
            if "application/json" in response.headers.get("Content-Type", ""):
                return response.json()
                
            # For HTML responses, return a simplified response
            return {"html": response.text}
        except requests.RequestException as e:
            logger.error(f"SEC EDGAR API error: {e}")
            raise ValueError(f"Error fetching data from SEC EDGAR: {e}")
            
    def search_company(self, company_name: str) -> Optional[Dict]:
        """
        Search for a company in the SEC EDGAR database.
        
        Args:
            company_name: The company name to search for
            
        Returns:
            Dictionary with company information including CIK if found,
            None otherwise
        """
        if not self.enabled:
            logger.info("EDGAR integration is disabled")
            return None
            
        # Check cache first
        cache_key = f"search_{company_name}"
        cached = self._get_cached_response(cache_key)
        
        if cached:
            logger.info(f"Using cached EDGAR search results for '{company_name}'")
            return cached
            
        # Prepare API request parameters
        params = {
            "company": company_name,
            "owner": "exclude",
            "action": "getcompany",
            "output": "json",
        }
        
        # Make the API request
        logger.info(f"Searching SEC EDGAR for company '{company_name}'")
        try:
            response = self._make_api_request(EDGAR_SEARCH_URL, params)
            self._cache_response(cache_key, response)
            return response
        except ValueError:
            logger.error(f"Company not found in EDGAR: {company_name}")
            return None
            
    def get_latest_filings(self, cik: str, count: int = 5) -> List[Dict]:
        """
        Get the latest filings for a company by CIK.
        
        Args:
            cik: The CIK number (with or without leading zeros)
            count: Maximum number of filings to retrieve
            
        Returns:
            List of filing dictionaries with form type, date, and URL
        """
        if not self.enabled:
            logger.info("EDGAR integration is disabled")
            return []
            
        # Normalize CIK (remove leading zeros)
        cik = cik.lstrip('0')
        
        # Check cache first
        cache_key = f"filings_{cik}"
        cached = self._get_cached_response(cache_key)
        
        if cached:
            logger.info(f"Using cached EDGAR filing data for CIK '{cik}'")
            return cached.get("filings", [])
            
        # Prepare API request parameters
        params = {
            "CIK": cik,
            "owner": "exclude",
            "action": "getcompany",
            "output": "json",
            "count": str(count),
        }
        
        # Make the API request
        logger.info(f"Fetching latest filings for CIK '{cik}'")
        try:
            response = self._make_api_request(EDGAR_SEARCH_URL, params)
            self._cache_response(cache_key, response)
            
            # Extract filings from response
            filings = []
            if "filings" in response and "recent" in response["filings"]:
                recent = response["filings"]["recent"]
                
                for i in range(min(count, len(recent.get("filingDate", [])))):
                    filing = {
                        "form": recent.get("form", [])[i] if i < len(recent.get("form", [])) else "Unknown",
                        "filing_date": recent.get("filingDate", [])[i] if i < len(recent.get("filingDate", [])) else "",
                        "accession_number": recent.get("accessionNumber", [])[i] if i < len(recent.get("accessionNumber", [])) else "",
                        "filing_url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{recent.get('accessionNumber', [])[i].replace('-', '')}/{recent.get('primaryDocument', [])[i]}" if i < len(recent.get("accessionNumber", [])) and i < len(recent.get("primaryDocument", [])) else "",
                    }
                    filings.append(filing)
                    
            return filings
        except ValueError:
            logger.error(f"Could not retrieve filings for CIK: {cik}")
            return []
            
    def extract_cik(self, response: Dict) -> Optional[str]:
        """
        Extract the CIK number from an EDGAR API response.
        
        Args:
            response: EDGAR API response
            
        Returns:
            CIK number if found, None otherwise
        """
        if not response:
            return None
            
        # Check for CIK in JSON response
        if "cik" in response:
            return response["cik"]
            
        if "CIK" in response:
            return response["CIK"]
            
        # Check for CIK in structured response
        try:
            if "companies" in response and len(response["companies"]) > 0:
                return response["companies"][0]["cik"]
        except (KeyError, TypeError, IndexError):
            pass
            
        # If response is HTML, try to extract CIK with regex
        if "html" in response:
            html = response["html"]
            cik_match = re.search(r'CIK=(\d+)', html)
            if cik_match:
                return cik_match.group(1)
                
        return None
        
    def enrich_entity(self, entity: CorporateEntity) -> CorporateEntity:
        """
        Enrich a CorporateEntity with SEC EDGAR information.
        
        Args:
            entity: The CorporateEntity to enrich
            
        Returns:
            The enriched CorporateEntity
        """
        if not self.enabled:
            logger.info("EDGAR integration is disabled")
            return entity
            
        logger.info(f"Enriching entity {entity.name} with SEC EDGAR data")
        
        # Search for the company
        search_response = self.search_company(entity.name)
        if not search_response:
            logger.info(f"No EDGAR data found for {entity.name}")
            return entity
            
        # Extract CIK
        cik = self.extract_cik(search_response)
        if not cik:
            logger.warning(f"Could not extract CIK for {entity.name}")
            return entity
            
        # Get latest filings
        filings = self.get_latest_filings(cik, count=3)
        
        # Add SEC information to entity notes
        sec_notes = [f"SEC CIK: {cik}"]
        
        if filings:
            sec_notes.append("\nLatest SEC Filings:")
            for filing in filings:
                sec_notes.append(f"- {filing['form']} ({filing['filing_date']}): {filing['filing_url']}")
                
        # Update entity notes
        if entity.notes:
            entity.notes += "\n\n" + "\n".join(sec_notes)
        else:
            entity.notes = "\n".join(sec_notes)
            
        return entity
"""