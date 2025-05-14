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
        # For URL-based search
        params: Dict[str, Any] = {
            "query": name,
            "limit": 25  # Limit results to 25
        }
        
        # For JSON-based search (more powerful)
        json_data = {
            "query": name,
            "limit": 25
        }
        
        # Add state filter if provided
        if state:
            json_data["filter"] = {
                "relation": "equals",
                "attribute": "state",
                "value": state.upper()
            }
        
        try:
            # Try the places search endpoint with JSON body as recommended
            response = await self.client.post("/places/search", json=json_data)
            response.raise_for_status()
            data = response.json()
            
            # Check if we have documents in the response
            if not data or "documents" not in data or not data["documents"]:
                # Try alternative search with URL params
                response = await self.client.get("/places/search", params=params)
                response.raise_for_status()
                data = response.json()
                
                if not data or "documents" not in data or not data["documents"]:
                    logger.info(f"No results found for '{name}' in {state or 'all states'}")
                    return []
            
            # Parse and normalize the results
            documents = data.get("documents", [])
            entities = [self._parse_document(doc) for doc in documents]
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
            # First try with the places endpoint
            response = await self.client.get(f"/places/{business_id}")
            response.raise_for_status()
            data = response.json()
            
            if not data:
                logger.info(f"No business found with ID '{business_id}'")
                return None
            
            return self._parse_document(data)
            
        except Exception as e:
            logger.error(f"Error fetching business by ID from Data Axle API: {e}")
            return None
    
    def _parse_document(self, data: Dict[str, Any]) -> Optional[CorporateEntity]:
        """
        Parse Data Axle places API response into a CorporateEntity.
        
        Args:
            data: Dictionary containing business place data from Data Axle
            
        Returns:
            CorporateEntity if parsing successful, None otherwise
        """
        try:
            # Extract basic information
            name = data.get("name", "")
            if not name:
                logger.warning("Skipping entity with missing name")
                return None
            
            # Extract jurisdiction (state code)
            jurisdiction = data.get("state", "")
            if not jurisdiction:
                logger.warning(f"Missing jurisdiction for '{name}'")
                jurisdiction = "US"  # Default to US if no state code
            
            # Map status - Data Axle places might not have status, so default to ACTIVE
            status = DEFAULT_STATUS
            
            # Parse date formed (need to check if different fields might have this)
            formed = None
            if year_founded := data.get("year_founded") or data.get("year_established"):
                try:
                    # If only year is provided, use January 1st
                    if isinstance(year_founded, int) or (isinstance(year_founded, str) and year_founded.isdigit()):
                        formed = datetime.date(int(year_founded), 1, 1)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid date format for '{name}': {year_founded}")
            
            # Extract officers (contacts)
            officers = []
            if primary_contact := data.get("primary_contact"):
                if isinstance(primary_contact, dict):
                    first_name = primary_contact.get("first_name", "")
                    last_name = primary_contact.get("last_name", "")
                    title = primary_contact.get("professional_title", "")
                    
                    if first_name or last_name:
                        contact_name = f"{first_name} {last_name}".strip()
                        if title:
                            contact_name += f", {title}"
                        officers.append(contact_name)
            
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
            if address := data.get("street"):
                city = data.get("city", "")
                state = data.get("state", "")
                zip_code = data.get("zip", "")
                full_address = f"Address: {address}, {city}, {state} {zip_code}".strip().replace(", ,", ",")
                notes_items.append(full_address)
                
            if phone := data.get("phone"):
                notes_items.append(f"Phone: {phone}")
                
            if website := data.get("website"):
                notes_items.append(f"Website: {website}")
                
            if sic_codes := data.get("sic_code_ids"):
                notes_items.append(f"SIC Codes: {', '.join(sic_codes) if isinstance(sic_codes, list) else sic_codes}")
                
            if data.get("employee_count"):
                notes_items.append(f"Employees: {data['employee_count']}")
                
            if sales := data.get("location_sales_volume") or data.get("sales_volume"):
                notes_items.append(f"Annual Sales: ${sales}")
            
            if notes_items:
                entity.notes = "\n".join(notes_items)
            
            return entity
            
        except Exception as e:
            logger.error(f"Error parsing place data from Data Axle API: {e}")
            return None
            
    def _parse_entity(self, data: Dict[str, Any]) -> Optional[CorporateEntity]:
        """
        Parse Data Axle API legacy response into a CorporateEntity.
        
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