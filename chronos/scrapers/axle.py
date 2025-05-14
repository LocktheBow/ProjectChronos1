"""
chronos.scrapers.axle
====================

Data Axle Platform (Direct+) scraper for business entity data.

This module implements a scraper for the Data Axle Platform API, providing
access to business entity data across multiple jurisdictions. It normalizes
the response data to match Chronos' internal data model.
"""

import logging
import datetime
from typing import Dict, List, Optional, Any, cast
from httpx import AsyncClient, Response

from chronos.models import CorporateEntity, Status
from .base import BaseScraper

logger = logging.getLogger(__name__)

# Mapping of Data Axle status values to Chronos Status enum
STATUS_MAP = {
    "active": Status.ACTIVE,
    "in business": Status.ACTIVE,
    "good standing": Status.IN_COMPLIANCE,
    "inactive": Status.DISSOLVED,
    "dissolved": Status.DISSOLVED,
    "canceled": Status.DISSOLVED,
    "revoked": Status.DELINQUENT,
    "forfeited": Status.DELINQUENT,
    "pending": Status.PENDING,
    # Add more mappings as needed
}

# Default status when no mapping exists
DEFAULT_STATUS = Status.ACTIVE


class DataAxleScraper(BaseScraper):
    """
    Data Axle API scraper for business entity data.
    
    This scraper retrieves business entity data from the Data Axle Platform API
    and normalizes it to the Chronos CorporateEntity model.
    """
    
    def __init__(self, client: AsyncClient):
        """
        Initialize the Data Axle scraper.
        
        Args:
            client: AsyncClient configured with Data Axle API credentials
        """
        self.client = client
    
    async def search(self, name: str, state: Optional[str] = None) -> List[CorporateEntity]:
        """
        Search for business entities by name and optional state.
        
        Args:
            name: Business name to search for
            state: Optional two-letter state code to filter results
            
        Returns:
            List of CorporateEntity objects matching the search criteria
        """
        params: Dict[str, Any] = {
            "company_name": name,
            "limit": 100  # Adjust as needed, balancing coverage vs. quota
        }
        
        if state:
            params["state_code"] = state.upper()
        
        try:
            response = await self.client.get("/business-directory/businesses", params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data or not isinstance(data, list) or len(data) == 0:
                logger.info(f"No results found for '{name}' in {state or 'all states'}")
                return []
            
            # Parse and normalize the results
            entities = [self._parse_entity(result) for result in data]
            return [entity for entity in entities if entity is not None]
            
        except Exception as e:
            logger.error(f"Error searching Data Axle API: {e}")
            return []
    
    async def fetch_by_id(self, business_id: str) -> Optional[CorporateEntity]:
        """
        Fetch a specific business entity by its Data Axle ID.
        
        Args:
            business_id: Data Axle business ID
            
        Returns:
            CorporateEntity if found, None otherwise
        """
        try:
            response = await self.client.get(f"/business-directory/businesses/{business_id}")
            response.raise_for_status()
            data = response.json()
            
            if not data:
                logger.info(f"No business found with ID '{business_id}'")
                return None
            
            return self._parse_entity(data)
            
        except Exception as e:
            logger.error(f"Error fetching business by ID from Data Axle API: {e}")
            return None
    
    def _parse_entity(self, data: Dict[str, Any]) -> Optional[CorporateEntity]:
        """
        Parse Data Axle API response into a CorporateEntity.
        
        Args:
            data: Dictionary containing business entity data from Data Axle
            
        Returns:
            CorporateEntity if parsing successful, None otherwise
        """
        try:
            # Extract basic information
            name = data.get("company_name", "")
            if not name:
                logger.warning("Skipping entity with missing name")
                return None
            
            # Extract jurisdiction (state code)
            jurisdiction = data.get("state_code", "")
            if not jurisdiction:
                logger.warning(f"Missing jurisdiction for '{name}'")
                jurisdiction = "US"  # Default to US if no state code
            
            # Map status from Data Axle to Chronos status
            status_value = data.get("status", "").lower()
            status = STATUS_MAP.get(status_value, DEFAULT_STATUS)
            
            # Parse date formed (incorporation date)
            formed = None
            if date_str := data.get("year_established"):
                try:
                    # If only year is provided, use January 1st
                    if len(str(date_str)) == 4:
                        formed = datetime.date(int(date_str), 1, 1)
                    else:
                        # Handle other date formats if provided
                        pass
                except (ValueError, TypeError):
                    logger.warning(f"Invalid date format for '{name}': {date_str}")
            
            # Extract officers (executives)
            officers = []
            if exec_data := data.get("executives"):
                if isinstance(exec_data, list):
                    for exec_item in exec_data:
                        if exec_name := exec_item.get("name"):
                            officers.append(exec_name)
            
            # Create and return the entity
            entity = CorporateEntity(
                name=name,
                jurisdiction=jurisdiction,
                status=status,
                formed=formed,
                officers=officers
            )
            
            # Add any additional metadata as notes
            notes_items = []
            if data.get("sic_code"):
                notes_items.append(f"SIC Code: {data['sic_code']}")
            if data.get("naics_code"):
                notes_items.append(f"NAICS Code: {data['naics_code']}")
            if data.get("employees"):
                notes_items.append(f"Employees: {data['employees']}")
            if data.get("annual_sales"):
                notes_items.append(f"Annual Sales: ${data['annual_sales']}")
            
            if notes_items:
                entity.notes = "\n".join(notes_items)
            
            return entity
            
        except Exception as e:
            logger.error(f"Error parsing entity data from Data Axle API: {e}")
            return None