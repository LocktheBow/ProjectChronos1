"""
chronos.scrapers.openc
======================

OpenCorporates API wrapper for business entity search and retrieval.

This module provides a SoSScraper-compatible interface to the OpenCorporates API,
allowing search and fetch operations across multiple jurisdictions while conforming
to the Chronos data model.

Usage:
------
scraper = OpenCorporatesScraper()
entity = scraper.fetch("ACME LLC")  # Searches globally
entity = scraper.search("ACME", jurisdiction="de")  # Search in Delaware only

Environment Variables:
---------------------
OPENCORP_API_TOKEN: Your OpenCorporates API token for authenticated requests
                    Public requests are rate-limited to 10 per hour
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
from typing import Dict, List, Optional, Union, Any

from chronos.models import CorporateEntity, Status
from .base import SoSScraper

# Configure logging
logger = logging.getLogger(__name__)

# API Constants
OC_API_BASE = "https://api.opencorporates.com/v0.4"
OC_API_TOKEN = os.environ.get("OPENCORP_API_TOKEN")
CACHE_DURATION = timedelta(hours=24)

# Mapping from OpenCorporates status to Chronos Status enum
STATUS_MAPPING = {
    "Active": Status.ACTIVE,
    "In Compliance": Status.IN_COMPLIANCE,
    "Inactive": Status.DISSOLVED,
    "Dissolved": Status.DISSOLVED,
    "Delinquent": Status.DELINQUENT,
    "Pending": Status.PENDING,
    # Default fallbacks by pattern matching
    "good standing": Status.IN_COMPLIANCE,
    "active": Status.ACTIVE,
}

# Cache setup
CACHE_DB_PATH = Path(os.environ.get("CHRONOS_CACHE_DIR", ".")) / "chronos_cache.db"


class OpenCorporatesScraper(SoSScraper):
    """
    OpenCorporates API scraper for Secretary of State business entity data.
    
    Provides search and fetch functionality across all jurisdictions supported
    by OpenCorporates, with optional caching to reduce API calls.
    """
    
    def __init__(self, use_cache: bool = True):
        """
        Initialize the OpenCorporates scraper.
        
        Args:
            use_cache: Whether to cache API responses (defaults to True)
        """
        self.use_cache = use_cache
        self._setup_cache_if_needed()
        
    def _setup_cache_if_needed(self) -> None:
        """Create the cache database and tables if they don't exist."""
        if not self.use_cache:
            return
            
        if not CACHE_DB_PATH.parent.exists():
            CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()
        
        # Create cache tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS oc_search_cache (
            query TEXT,
            jurisdiction TEXT,
            response TEXT,
            timestamp TIMESTAMP,
            PRIMARY KEY (query, jurisdiction)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS oc_entity_cache (
            company_number TEXT,
            jurisdiction TEXT,
            response TEXT,
            timestamp TIMESTAMP,
            PRIMARY KEY (company_number, jurisdiction)
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def _get_cached_response(self, cache_type: str, key1: str, key2: str = '') -> Optional[Dict]:
        """
        Retrieve a cached response if it exists and is not expired.
        
        Args:
            cache_type: Either 'search' or 'entity'
            key1: Query or company_number
            key2: Jurisdiction code
            
        Returns:
            The cached response as a dict, or None if not found or expired
        """
        if not self.use_cache:
            return None
            
        table = f"oc_{cache_type}_cache"
        key_field = "query" if cache_type == "search" else "company_number"
        
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()
        
        # Convert empty string to None for SQL query
        key2_sql = key2 if key2 else None
        
        cursor.execute(f'''
        SELECT response, timestamp FROM {table}
        WHERE {key_field} = ? AND jurisdiction = ?
        ''', (key1, key2_sql))
        
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
        
    def _cache_response(self, cache_type: str, key1: str, key2: str, response: Dict) -> None:
        """
        Cache an API response.
        
        Args:
            cache_type: Either 'search' or 'entity'
            key1: Query or company_number
            key2: Jurisdiction code
            response: The API response to cache
        """
        if not self.use_cache:
            return
            
        table = f"oc_{cache_type}_cache"
        key_field = "query" if cache_type == "search" else "company_number"
        
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()
        
        # Convert empty string to None for SQL storage
        key2_sql = key2 if key2 else None
        
        # Store with current timestamp
        timestamp = datetime.now().isoformat()
        response_str = json.dumps(response)
        
        cursor.execute(f'''
        INSERT OR REPLACE INTO {table}
        ({key_field}, jurisdiction, response, timestamp)
        VALUES (?, ?, ?, ?)
        ''', (key1, key2_sql, response_str, timestamp))
        
        conn.commit()
        conn.close()
        
    def _make_api_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make a request to the OpenCorporates API.
        
        Args:
            endpoint: API endpoint path, relative to base URL
            params: Query parameters for the request
            
        Returns:
            JSON response as a dictionary
            
        Raises:
            ValueError: For API errors or invalid responses
        """
        url = f"{OC_API_BASE}/{endpoint}"
        headers = {"Accept": "application/json"}
        
        # Add API token if available
        request_params = params or {}
        if OC_API_TOKEN:
            request_params["api_token"] = OC_API_TOKEN
            
        try:
            response = requests.get(url, headers=headers, params=request_params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"OpenCorporates API error: {e}")
            raise ValueError(f"Error fetching data from OpenCorporates: {e}")
            
    def _map_oc_status_to_chronos(self, status_text: str) -> Status:
        """
        Map an OpenCorporates status string to a Chronos Status enum.
        
        Args:
            status_text: Status text from the OpenCorporates API
            
        Returns:
            Corresponding Chronos Status enum value
        """
        if not status_text:
            return Status.PENDING
            
        # Direct mapping lookup
        if status_text in STATUS_MAPPING:
            return STATUS_MAPPING[status_text]
            
        # Fuzzy matching based on substrings
        status_lower = status_text.lower()
        for key, value in STATUS_MAPPING.items():
            if key.lower() in status_lower:
                return value
                
        # Default fallback
        return Status.ACTIVE
        
    def _parse_oc_date(self, date_str: Optional[str]) -> date:
        """
        Parse an OpenCorporates date string into a Python date object.
        
        Args:
            date_str: Date string from OpenCorporates API
            
        Returns:
            Python date object, or today's date if parsing fails
        """
        if not date_str:
            return date.today()
            
        try:
            # OpenCorporates uses ISO format dates (YYYY-MM-DD)
            return date.fromisoformat(date_str)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date: {date_str}, using today's date")
            return date.today()
            
    def _company_data_to_entity(self, company_data: Dict) -> CorporateEntity:
        """
        Convert OpenCorporates company data to a Chronos CorporateEntity.
        
        Args:
            company_data: Company data from OpenCorporates API
            
        Returns:
            Chronos CorporateEntity object
        """
        # Extract and normalize the jurisdiction code
        jurisdiction = company_data.get("jurisdiction_code", "").upper()
        if jurisdiction and "_" in jurisdiction:
            # Convert "us_de" format to "DE" format
            jurisdiction = jurisdiction.split("_")[1].upper()
            
        # Extract the company status
        status_text = company_data.get("current_status") or company_data.get("status")
        status = self._map_oc_status_to_chronos(status_text)
        
        # Parse incorporation date
        incorporated = self._parse_oc_date(company_data.get("incorporation_date"))
        
        # Extract company name
        name = company_data.get("name", "Unknown Entity")
        
        # Create entity with basic information
        entity = CorporateEntity(
            name=name,
            jurisdiction=jurisdiction,
            formed=incorporated,
            status=status,
        )
        
        # Add officers if available
        officers = company_data.get("officers", [])
        if officers:
            entity.officers = [officer.get("name", "") for officer in officers if "name" in officer]
            
        # Add notes if there's additional information
        notes = []
        
        if company_data.get("company_number"):
            notes.append(f"Company Number: {company_data['company_number']}")
            
        if company_data.get("company_type"):
            notes.append(f"Company Type: {company_data['company_type']}")
            
        if company_data.get("registered_address"):
            address = company_data["registered_address"]
            notes.append(f"Registered Address: {address}")
            
        if company_data.get("opencorporates_url"):
            notes.append(f"OpenCorporates URL: {company_data['opencorporates_url']}")
            
        if notes:
            entity.notes = "\n".join(notes)
            
        return entity
        
    def search(self, query: str, jurisdiction: Optional[str] = None) -> List[CorporateEntity]:
        """
        Search for companies by name, optionally filtered by jurisdiction.
        
        Args:
            query: Company name or search term
            jurisdiction: Optional two-letter jurisdiction code (e.g., 'DE', 'CA')
            
        Returns:
            List of matching CorporateEntity objects
        """
        # Normalize jurisdiction to OpenCorporates format
        oc_jurisdiction = None
        if jurisdiction:
            jurisdiction = jurisdiction.upper()
            # For US states, OpenCorporates uses "us_XX" format
            if len(jurisdiction) == 2:
                oc_jurisdiction = f"us_{jurisdiction.lower()}"
                
        # Check cache first
        cache_jurisdiction = oc_jurisdiction or ""
        cached = self._get_cached_response("search", query, cache_jurisdiction)
        
        if cached:
            logger.info(f"Using cached search results for '{query}' in jurisdiction '{jurisdiction}'")
            results = cached
        else:
            # Prepare API request parameters
            params = {"q": query}
            if oc_jurisdiction:
                params["jurisdiction_code"] = oc_jurisdiction
                
            # Make the API request
            logger.info(f"Searching OpenCorporates for '{query}' in jurisdiction '{jurisdiction}'")
            response = self._make_api_request("companies/search", params)
            
            # Cache the response
            self._cache_response("search", query, cache_jurisdiction, response)
            results = response
            
        # Extract companies from response
        companies = []
        try:
            results_obj = results.get("results", {})
            if "companies" in results_obj:
                companies = [comp.get("company", {}) for comp in results_obj.get("companies", [])]
            elif "company" in results_obj:
                # Single company result
                companies = [results_obj["company"]]
        except (KeyError, TypeError, AttributeError) as e:
            logger.error(f"Error parsing OpenCorporates response: {e}")
            return []
            
        # Convert to CorporateEntity objects
        entities = [self._company_data_to_entity(company) for company in companies]
        return entities
        
    def fetch(self, name: str) -> Optional[CorporateEntity]:
        """
        Fetch a company by name.
        
        This implementation searches for the company name and returns the best match.
        
        Args:
            name: Company name to search for
            
        Returns:
            CorporateEntity if found, None otherwise
        """
        # Search globally for exact name match
        results = self.search(name)
        
        if not results:
            return None
            
        # Find the best match by comparing names
        best_match = None
        name_lower = name.lower()
        
        for entity in results:
            entity_name_lower = entity.name.lower()
            
            # Exact match is best
            if entity_name_lower == name_lower:
                return entity
                
            # If exact match not found, prefer starts-with match
            if entity_name_lower.startswith(name_lower) and (best_match is None or 
                                                            len(entity.name) < len(best_match.name)):
                best_match = entity
                
        # If no starts-with match, return the first result
        return best_match or results[0]
        
    def fetch_by_id(self, company_number: str, jurisdiction: str) -> Optional[CorporateEntity]:
        """
        Fetch a company by its company number and jurisdiction.
        
        Args:
            company_number: The company registration number
            jurisdiction: Jurisdiction code (e.g. 'DE', 'CA')
            
        Returns:
            CorporateEntity if found, None otherwise
        """
        # Normalize jurisdiction to OpenCorporates format
        jurisdiction = jurisdiction.upper()
        oc_jurisdiction = jurisdiction.lower()
        if len(jurisdiction) == 2:
            oc_jurisdiction = f"us_{jurisdiction.lower()}"
            
        # Check cache first
        cached = self._get_cached_response("entity", company_number, oc_jurisdiction)
        
        if cached:
            logger.info(f"Using cached entity data for '{company_number}' in jurisdiction '{jurisdiction}'")
            response = cached
        else:
            # Make the API request
            endpoint = f"companies/{oc_jurisdiction}/{company_number}"
            logger.info(f"Fetching company '{company_number}' from jurisdiction '{jurisdiction}'")
            
            try:
                response = self._make_api_request(endpoint)
                # Cache the response
                self._cache_response("entity", company_number, oc_jurisdiction, response)
            except ValueError:
                logger.error(f"Company not found: {company_number} in {jurisdiction}")
                return None
                
        # Extract company data from response
        try:
            company_data = response.get("results", {}).get("company", {})
            if not company_data:
                return None
                
            return self._company_data_to_entity(company_data)
        except (KeyError, TypeError, AttributeError) as e:
            logger.error(f"Error parsing OpenCorporates company data: {e}")
            return None