"""
chronos.scrapers.cobalt
=======================

Cobalt Intelligence API client for business entity data.

This module implements a scraper for the Cobalt Intelligence API, providing
access to Secretary of State business entity data across all 50 US states.
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

# Base URL for Cobalt Intelligence API
BASE_URL = str(settings.cobalt_base)

# Default API key from settings
API_KEY = settings.cobalt_api_key

# Mapping of Cobalt Intelligence status values to Chronos Status enum
STATUS_MAP = {
    "active": Status.ACTIVE,
    "good standing": Status.IN_COMPLIANCE,
    "in good standing": Status.IN_COMPLIANCE,
    "dissolved": Status.DISSOLVED,
    "inactive": Status.DISSOLVED,
    "revoked": Status.DELINQUENT,
    "delinquent": Status.DELINQUENT,
    "suspended": Status.DELINQUENT,
    "pending": Status.PENDING,
    # Add more mappings as needed
}

# Default status when no mapping exists
DEFAULT_STATUS = Status.ACTIVE


class CobaltScraper(BaseScraper):
    """
    Cobalt Intelligence API scraper for business entity data.
    
    This scraper retrieves business entity data from the Cobalt Intelligence API
    and normalizes it to the Chronos CorporateEntity model.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Cobalt Intelligence scraper.
        
        Args:
            api_key: Optional API key for Cobalt Intelligence API
        """
        self.api_key = api_key or API_KEY
        if not self.api_key:
            logger.warning("No Cobalt Intelligence API key provided. Set COBALT_API_KEY environment variable.")
    
    async def search(
        self, 
        name: Optional[str] = None, 
        state: Optional[str] = None,
        sos_id: Optional[str] = None,
        person_first_name: Optional[str] = None,
        person_last_name: Optional[str] = None,
        retry_id: Optional[str] = None,
        street: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        live_data: bool = True,
        include_screenshot: bool = False,
        include_ucc_data: bool = False
    ) -> List[CorporateEntity]:
        """
        Search for business entities using the Cobalt Intelligence API.
        
        Args:
            name: Business name to search for (searchQuery parameter)
            state: State code to filter results
            sos_id: Secretary of State/Entity ID to search for
            person_first_name: Person's first name to search for
            person_last_name: Person's last name to search for
            retry_id: ID for checking status of long-running requests
            street: Street address to filter results
            city: City to filter results
            zip_code: ZIP code to filter results
            live_data: Whether to get live data (True) or cached data (False)
            include_screenshot: Whether to include screenshots in results
            include_ucc_data: Whether to include UCC (lien) data in results
            
        Returns:
            List of CorporateEntity objects matching the search criteria
        """
        try:
            # Prepare request headers
            headers = {
                "x-api-key": self.api_key,
                "Accept": "application/json"
            }
            
            # Prepare search parameters
            params = {}
            
            # Add main search parameter (at least one is required)
            if name:
                params["searchQuery"] = name
            elif sos_id:
                params["sosId"] = sos_id
            elif person_first_name and person_last_name:
                params["searchByPersonFirstName"] = person_first_name
                params["searchByPersonLastName"] = person_last_name
            elif retry_id:
                params["retryId"] = retry_id
            else:
                raise ValueError("Either name, sos_id, person name, or retry_id must be provided")
            
            # Add state filter if provided (required unless using retry_id)
            if state:
                params["state"] = state
            elif not retry_id:
                raise ValueError("State is required unless using retry_id")
                
            # Add optional filters
            if street:
                params["street"] = street
            if city:
                params["city"] = city
            if zip_code:
                params["zip"] = zip_code
                
            # Add data configuration options
            params["liveData"] = str(live_data).lower()
            if include_screenshot:
                params["screenshot"] = "true"
            if include_ucc_data:
                params["uccData"] = "true"
            
            # Make the API call synchronously (can be updated to async)
            search_type = name or sos_id or f"{person_first_name} {person_last_name}" or retry_id
            logger.info(f"Searching Cobalt Intelligence for '{search_type}' in {state or 'based on retry_id'}")
            response = requests.get(
                f"{BASE_URL}/search", 
                headers=headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            # Check if we have results
            if not data or "results" not in data:
                logger.info(f"No results found for '{name}' in {state or 'all states'}")
                return []
            
            # Parse results into CorporateEntity objects
            entities = []
            results = data.get("results", [])
            
            for result in results:
                entity = self._parse_search_result(result)
                if entity:
                    entities.append(entity)
            
            logger.info(f"Found {len(entities)} entities matching '{name}' in {state or 'all states'}")
            return entities
            
        except Exception as e:
            logger.error(f"Error searching Cobalt Intelligence API: {e}")
            return []
    
    async def get_details(self, name: str, state: str) -> Optional[CorporateEntity]:
        """
        Get detailed information for a specific business entity.
        
        Args:
            name: Business name to search for
            state: State code where the business is registered
            
        Returns:
            CorporateEntity if found, None otherwise
        """
        try:
            # Prepare request headers
            headers = {
                "x-api-key": self.api_key,
                "Accept": "application/json"
            }
            
            # Make the API call
            logger.info(f"Fetching details for '{name}' in {state}")
            url = f"{BASE_URL}/business-details"
            params = {
                "businessName": name,
                "state": state
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Parse the business details into a CorporateEntity
            if data:
                return self._parse_business_details(data)
            else:
                logger.info(f"No details found for '{name}' in {state}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching business details from Cobalt Intelligence API: {e}")
            return None
    
    def _parse_search_result(self, data: Dict[str, Any]) -> Optional[CorporateEntity]:
        """
        Parse a search result into a CorporateEntity.
        
        Args:
            data: Dictionary containing business data from search result
            
        Returns:
            CorporateEntity if parsing successful, None otherwise
        """
        try:
            # Extract basic information - check both title and businessName fields
            name = data.get("title", "") or data.get("businessName", "") or data.get("searchResultTitle", "")
            if not name:
                logger.warning("Skipping entity with missing name")
                return None
            
            # Extract jurisdiction - check multiple fields
            jurisdiction = (
                data.get("stateOfSosRegistration", "") or 
                data.get("stateOfFormation", "") or
                data.get("physicalAddressState", "") or
                data.get("state", "")
            )
            if not jurisdiction:
                logger.warning(f"Missing jurisdiction for '{name}'")
                jurisdiction = "US"  # Default to US if no jurisdiction
            
            # Map status from Cobalt to Chronos status
            status_value = data.get("normalizedStatus", "") or data.get("status", "")
            status_value = status_value.lower() if status_value else ""
            status = STATUS_MAP.get(status_value, DEFAULT_STATUS)
            
            # Parse date formed - check multiple date fields
            formed = None
            if filing_date := data.get("normalizedFilingDate", "") or data.get("filingDate", ""):
                try:
                    # Handle multiple date formats
                    if "T" in filing_date:
                        # ISO format with time component
                        try:
                            formed = datetime.datetime.fromisoformat(filing_date.replace('Z', '+00:00')).date()
                        except ValueError:
                            try:
                                formed = datetime.datetime.strptime(filing_date.split('T')[0], "%Y-%m-%d").date()
                            except ValueError:
                                logger.warning(f"Failed to parse ISO date: {filing_date}")
                    elif "-" in filing_date:
                        # Try various date formats with dashes
                        date_formats = ["%Y-%m-%d", "%m-%d-%Y"]
                        for fmt in date_formats:
                            try:
                                formed = datetime.datetime.strptime(filing_date, fmt).date()
                                break
                            except ValueError:
                                continue
                    elif "/" in filing_date:
                        # Try formats with slashes
                        date_formats = ["%m/%d/%Y", "%Y/%m/%d"]
                        for fmt in date_formats:
                            try:
                                formed = datetime.datetime.strptime(filing_date, fmt).date()
                                break
                            except ValueError:
                                continue
                    else:
                        # Try to extract a year from any format
                        import re
                        year_match = re.search(r'(\d{4})', filing_date)
                        if year_match:
                            year = int(year_match.group(1))
                            if 1800 <= year <= 2100:  # Sanity check
                                formed = datetime.date(year, 1, 1)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid date format for '{name}': {filing_date}. Error: {e}")
            
            # Extract officers
            officers = []
            if officer_data := data.get("officers", []):
                for officer in officer_data:
                    if officer_name := officer.get("name"):
                        title = officer.get("title", "")
                        if title:
                            officers.append(f"{officer_name} ({title})")
                        else:
                            officers.append(officer_name)
            
            # Extract additional metadata for notes
            notes_items = []
            
            # Add entity details
            if entity_type := data.get("entityType"):
                notes_items.append(f"Entity Type: {entity_type}")
                if entity_subtype := data.get("entitySubType"):
                    notes_items.append(f"Entity Subtype: {entity_subtype}")
                
            if sos_id := data.get("sosId"):
                notes_items.append(f"SoS ID: {sos_id}")
                
            if status_detail := data.get("status"):
                notes_items.append(f"Status Detail: {status_detail}")
                
            if ein := data.get("EIN"):
                notes_items.append(f"EIN: {ein}")
                
            if tax_number := data.get("taxPayerNumber"):
                notes_items.append(f"Tax ID: {tax_number}")
                
            if industry := data.get("industry"):
                notes_items.append(f"Industry: {industry}")
                
            if confidence := data.get("confidenceLevel"):
                notes_items.append(f"Confidence Level: {confidence}")
                
            if ai_confidence := data.get("aiConfidenceLevel"):
                notes_items.append(f"AI Confidence: {ai_confidence}")
                
            if next_report := data.get("nextReportDueDate"):
                notes_items.append(f"Next Report Due: {next_report}")
                
            # Add agent information
            if agent_name := data.get("agentName"):
                agent_info = f"Registered Agent: {agent_name}"
                
                # Check if agent is commercial
                if data.get("agentIsCommercial") is not None:
                    agent_info += f" (Commercial: {data.get('agentIsCommercial')})"
                    
                notes_items.append(agent_info)
                
                # Add agent address if available
                agent_address_parts = []
                if addr := data.get("agentStreetAddress"):
                    agent_address_parts.append(addr)
                if city := data.get("agentCity"):
                    agent_address_parts.append(city)
                if state := data.get("agentState"):
                    agent_address_parts.append(state)
                if zip_code := data.get("agentZip"):
                    agent_address_parts.append(zip_code)
                    
                if agent_address_parts:
                    notes_items.append(f"Agent Address: {', '.join(agent_address_parts)}")
                    
                # Check if agent resigned
                if data.get("agentResigned"):
                    if resigned_date := data.get("agentResignedDate"):
                        notes_items.append(f"Agent Resigned: {resigned_date}")
                    else:
                        notes_items.append("Agent Resigned: Yes")
            
            # Add physical address
            physical_address_parts = []
            if addr := data.get("physicalAddressStreet"):
                physical_address_parts.append(addr)
            if city := data.get("physicalAddressCity"):
                physical_address_parts.append(city)
            if state := data.get("physicalAddressState"):
                physical_address_parts.append(state)
            if zip_code := data.get("physicalAddressZip"):
                physical_address_parts.append(zip_code)
                
            if physical_address_parts:
                notes_items.append(f"Physical Address: {', '.join(physical_address_parts)}")
                
            # Add mailing address if different from physical
            mailing_address_parts = []
            if addr := data.get("mailingAddressStreet"):
                mailing_address_parts.append(addr)
            if city := data.get("mailingAddressCity"):
                mailing_address_parts.append(city)
            if state := data.get("mailingAddressState"):
                mailing_address_parts.append(state)
            if zip_code := data.get("mailingAddressZip"):
                mailing_address_parts.append(zip_code)
                
            if mailing_address_parts and mailing_address_parts != physical_address_parts:
                notes_items.append(f"Mailing Address: {', '.join(mailing_address_parts)}")
                
            # Add contact info
            if phone := data.get("phoneNumber"):
                notes_items.append(f"Phone: {phone}")
                
            if email := data.get("email"):
                notes_items.append(f"Email: {email}")
                
            if url := data.get("url"):
                notes_items.append(f"Website: {url}")
                
            # Add document links
            if documents := data.get("documents", []):
                doc_links = []
                for doc in documents[:3]:  # Limit to first 3 documents to avoid excessive notes
                    if doc_name := doc.get("name"):
                        if doc_url := doc.get("url"):
                            doc_links.append(f"{doc_name}: {doc_url}")
                        else:
                            doc_links.append(doc_name)
                            
                if doc_links:
                    notes_items.append(f"Documents: {'; '.join(doc_links)}")
                    
            # Add screenshot URL if available
            if screenshot := data.get("screenshotUrl"):
                notes_items.append(f"Screenshot: {screenshot}")
                
            # Add assumed business names
            if assumed_names := data.get("assumedBusinessNames", []):
                dba_names = []
                for dba in assumed_names:
                    if dba_title := dba.get("title"):
                        dba_names.append(dba_title)
                        
                if dba_names:
                    notes_items.append(f"DBA Names: {', '.join(dba_names)}")
                    
            # Note important dates
            if inactive_date := data.get("inactiveDate"):
                notes_items.append(f"Inactive Date: {inactive_date}")
            
            # Create the entity with parsed data
            entity = CorporateEntity(
                name=name,
                jurisdiction=jurisdiction,
                status=status,
                formed=formed,
                officers=officers,
                notes="\n".join(notes_items) if notes_items else None
            )
            
            return entity
            
        except Exception as e:
            logger.error(f"Error parsing search result from Cobalt Intelligence API: {e}")
            logger.debug(f"Problematic data: {data}")
            return None
    
    def _parse_business_details(self, data: Dict[str, Any]) -> Optional[CorporateEntity]:
        """
        Parse business details into a CorporateEntity.
        
        Args:
            data: Dictionary containing detailed business data
            
        Returns:
            CorporateEntity if parsing successful, None otherwise
        """
        try:
            # Extract basic information
            name = data.get("businessName", "")
            if not name:
                logger.warning("Skipping entity with missing name")
                return None
            
            # Extract jurisdiction from state field
            jurisdiction = data.get("state", "")
            if not jurisdiction:
                logger.warning(f"Missing jurisdiction for '{name}'")
                jurisdiction = "US"  # Default to US if no jurisdiction
            
            # Map status from Cobalt to Chronos status
            status_value = data.get("status", "").lower()
            status = STATUS_MAP.get(status_value, DEFAULT_STATUS)
            
            # Parse date formed/registered
            formed = None
            if filing_date := data.get("normalizedFilingDate", "") or data.get("filingDate", ""):
                try:
                    # Handle multiple date formats
                    if "T" in filing_date:
                        # ISO format with time component
                        try:
                            formed = datetime.datetime.fromisoformat(filing_date.replace('Z', '+00:00')).date()
                        except ValueError:
                            try:
                                formed = datetime.datetime.strptime(filing_date.split('T')[0], "%Y-%m-%d").date()
                            except ValueError:
                                logger.warning(f"Failed to parse ISO date: {filing_date}")
                    elif "-" in filing_date:
                        # Try various date formats with dashes
                        date_formats = ["%Y-%m-%d", "%m-%d-%Y"]
                        for fmt in date_formats:
                            try:
                                formed = datetime.datetime.strptime(filing_date, fmt).date()
                                break
                            except ValueError:
                                continue
                    elif "/" in filing_date:
                        # Try formats with slashes
                        date_formats = ["%m/%d/%Y", "%Y/%m/%d"]
                        for fmt in date_formats:
                            try:
                                formed = datetime.datetime.strptime(filing_date, fmt).date()
                                break
                            except ValueError:
                                continue
                    else:
                        # Try to extract a year from any format
                        import re
                        year_match = re.search(r'(\d{4})', filing_date)
                        if year_match:
                            year = int(year_match.group(1))
                            if 1800 <= year <= 2100:  # Sanity check
                                formed = datetime.date(year, 1, 1)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid date format for '{name}': {filing_date}. Error: {e}")
            
            # Extract additional metadata for notes
            notes_items = []
            
            if entity_type := data.get("entityType"):
                notes_items.append(f"Entity Type: {entity_type}")
                
            if filing_number := data.get("filingNumber"):
                notes_items.append(f"Filing Number: {filing_number}")
                
            if agent_name := data.get("registeredAgent", {}).get("name"):
                agent_address = data.get("registeredAgent", {}).get("address", "")
                notes_items.append(f"Registered Agent: {agent_name}")
                if agent_address:
                    notes_items.append(f"Agent Address: {agent_address}")
            
            if business_address := data.get("businessAddress"):
                notes_items.append(f"Business Address: {business_address}")
            
            if mailing_address := data.get("mailingAddress"):
                notes_items.append(f"Mailing Address: {mailing_address}")
            
            # Parse officers
            officers = []
            if officers_data := data.get("officers", []):
                for officer in officers_data:
                    if officer_name := officer.get("name"):
                        title = officer.get("title", "")
                        if title:
                            officers.append(f"{officer_name} ({title})")
                        else:
                            officers.append(officer_name)
            
            # Create the entity with parsed data
            entity = CorporateEntity(
                name=name,
                jurisdiction=jurisdiction,
                status=status,
                formed=formed,
                officers=officers,
                notes="\n".join(notes_items) if notes_items else None
            )
            
            return entity
            
        except Exception as e:
            logger.error(f"Error parsing business details from Cobalt Intelligence API: {e}")
            logger.debug(f"Problematic data: {data}")
            return None