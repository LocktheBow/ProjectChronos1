"""
chronos.scrapers.opencorp
=======================

OpenCorporates API client for business entity data.

This module implements a scraper for the OpenCorporates API, providing
access to business entity data across multiple jurisdictions worldwide.
It normalizes the response data to match Chronos' internal data model.
"""

import os
import logging
import datetime
import requests
from typing import List, Optional, Dict, Any

from chronos.models import CorporateEntity, Status
from chronos.settings import settings
from .base import BaseScraper

logger = logging.getLogger(__name__)

# Base URL for OpenCorporates API
BASE_URL = str(settings.opencorp_base)

# Default API token from settings
API_TOKEN = settings.opencorp_api_token

# Mapping of OpenCorporates status values to Chronos Status enum
STATUS_MAP = {
    "active": Status.ACTIVE,
    "good standing": Status.IN_COMPLIANCE,
    "dissolved": Status.DISSOLVED,
    "inactive": Status.DISSOLVED,
    "revoked": Status.DELINQUENT,
    "suspended": Status.DELINQUENT,
    "pending": Status.PENDING,
    # Add more mappings as needed
}

# Default status when no mapping exists
DEFAULT_STATUS = Status.ACTIVE


class OpenCorporatesScraper(BaseScraper):
    """
    OpenCorporates API scraper for business entity data.
    
    This scraper retrieves business entity data from the OpenCorporates API
    and normalizes it to the Chronos CorporateEntity model.
    """
    
    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize the OpenCorporates scraper.
        
        Args:
            api_token: Optional API token for OpenCorporates API
        """
        self.api_token = api_token or API_TOKEN
        if not self.api_token:
            logger.warning("No OpenCorporates API token provided. Set OPENCORP_API_TOKEN environment variable.")
    
    async def search(self, name: str, state: Optional[str] = None) -> List[CorporateEntity]:
        """
        Search for business entities by name and optional state.
        
        Args:
            name: Business name to search for
            state: Optional two-letter state code to filter results
            
        Returns:
            List of CorporateEntity objects matching the search criteria
        """
        try:
            # Prepare search parameters
            params = {
                "q": name,
                "api_token": self.api_token,
                "per_page": 10  # Limit to 10 results by default
            }
            
            # Add jurisdiction filter if state is provided
            if state:
                # OpenCorporates uses 'us_XX' format for US states
                jurisdiction = f"us_{state.lower()}"
                params["jurisdiction_code"] = jurisdiction
            
            # Make the API call synchronously (can be updated to async)
            logger.info(f"Searching OpenCorporates for '{name}' in {state or 'all jurisdictions'}")
            response = requests.get(f"{BASE_URL}/companies/search", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract companies from the response
            if not data or "results" not in data or "companies" not in data["results"]:
                logger.info(f"No results found for '{name}' in {state or 'all jurisdictions'}")
                return []
            
            # Parse each company into a CorporateEntity
            companies = data["results"]["companies"]
            entities = []
            for company_data in companies:
                company = company_data.get("company", {})
                entity = self._parse_company(company)
                if entity:
                    entities.append(entity)
            
            logger.info(f"Found {len(entities)} entities matching '{name}' in {state or 'all jurisdictions'}")
            return entities
            
        except Exception as e:
            logger.error(f"Error searching OpenCorporates API: {e}")
            return []
    
    async def fetch_by_id(self, company_id: str, jurisdiction: str) -> Optional[CorporateEntity]:
        """
        Fetch a specific business entity by its OpenCorporates ID.
        
        Args:
            company_id: OpenCorporates company ID
            jurisdiction: Jurisdiction code (e.g., 'us_de' for Delaware)
            
        Returns:
            CorporateEntity if found, None otherwise
        """
        try:
            # Make the API call
            logger.info(f"Fetching company with ID: {company_id} in {jurisdiction}")
            url = f"{BASE_URL}/companies/{jurisdiction}/{company_id}"
            response = requests.get(url, params={"api_token": self.api_token})
            response.raise_for_status()
            data = response.json()
            
            # Extract and parse the company data
            if not data or "results" not in data or "company" not in data["results"]:
                logger.info(f"No company found with ID '{company_id}' in {jurisdiction}")
                return None
            
            company = data["results"]["company"]
            return self._parse_company(company)
            
        except Exception as e:
            logger.error(f"Error fetching company by ID from OpenCorporates API: {e}")
            return None
    
    async def fetch_officers(self, company_id: str, jurisdiction: str) -> List[str]:
        """
        Fetch officers for a specific company.
        
        Args:
            company_id: OpenCorporates company ID
            jurisdiction: Jurisdiction code (e.g., 'us_de' for Delaware)
            
        Returns:
            List of officer names
        """
        try:
            # Make the API call
            logger.info(f"Fetching officers for company ID: {company_id} in {jurisdiction}")
            url = f"{BASE_URL}/companies/{jurisdiction}/{company_id}/officers"
            response = requests.get(url, params={"api_token": self.api_token})
            response.raise_for_status()
            data = response.json()
            
            # Extract officers from the response
            officers = []
            if data and "results" in data and "officers" in data["results"]:
                for officer_data in data["results"]["officers"]:
                    officer = officer_data.get("officer", {})
                    name = officer.get("name", "")
                    position = officer.get("position", "")
                    if name:
                        if position:
                            officers.append(f"{name} ({position})")
                        else:
                            officers.append(name)
            
            return officers
            
        except Exception as e:
            logger.error(f"Error fetching officers from OpenCorporates API: {e}")
            return []
    
    def _parse_company(self, data: Dict[str, Any]) -> Optional[CorporateEntity]:
        """
        Parse OpenCorporates company data into a CorporateEntity.
        
        Args:
            data: Dictionary containing company data from OpenCorporates
            
        Returns:
            CorporateEntity if parsing successful, None otherwise
        """
        try:
            # Extract basic information
            name = data.get("name", "")
            if not name:
                logger.warning("Skipping entity with missing name")
                return None
            
            # Extract jurisdiction - strip 'us_' prefix if present
            jurisdiction = data.get("jurisdiction_code", "").upper()
            if jurisdiction.startswith("US_"):
                jurisdiction = jurisdiction[3:]
            if not jurisdiction:
                jurisdiction = "US"  # Default to US if no jurisdiction
            
            # Map status from OpenCorporates to Chronos status
            status_value = data.get("current_status", "").lower()
            status = STATUS_MAP.get(status_value, DEFAULT_STATUS)
            
            # Parse date formed (incorporation date)
            formed = None
            if incorporation_date := data.get("incorporation_date"):
                try:
                    formed = datetime.date.fromisoformat(incorporation_date)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid date format for '{name}': {incorporation_date}")
            
            # Extract additional metadata for notes
            notes_items = []
            
            if company_number := data.get("company_number"):
                notes_items.append(f"Company Number: {company_number}")
                
            if company_type := data.get("company_type"):
                notes_items.append(f"Company Type: {company_type}")
                
            if registry_url := data.get("registry_url"):
                notes_items.append(f"Registry URL: {registry_url}")
                
            if opencorp_url := data.get("opencorporates_url"):
                notes_items.append(f"OpenCorporates URL: {opencorp_url}")
                
            if previous_names := data.get("previous_names"):
                if isinstance(previous_names, list) and previous_names:
                    prev_names_list = [p.get("company_name", "") for p in previous_names if p.get("company_name")]
                    if prev_names_list:
                        notes_items.append(f"Previous Names: {', '.join(prev_names_list)}")
            
            # Create the entity with parsed data
            entity = CorporateEntity(
                name=name,
                jurisdiction=jurisdiction,
                status=status,
                formed=formed,
                officers=[],  # Officers are fetched separately for performance reasons
                notes="\n".join(notes_items) if notes_items else None
            )
            
            return entity
            
        except Exception as e:
            logger.error(f"Error parsing company data from OpenCorporates API: {e}")
            logger.debug(f"Problematic data: {data}")
            return None