"""
api.cobalt
=========

FastAPI router for Cobalt Intelligence API integration.

This module implements endpoints for searching business entities using 
Cobalt Intelligence API and retrieving entity data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging

from chronos.models import CorporateEntity
from chronos.portfolio import PortfolioManager
from chronos.scrapers.cobalt import CobaltScraper
from .deps import get_portfolio, get_cobalt_scraper

# Create router
router = APIRouter(prefix="/cobalt", tags=["cobalt"])

# Configure logging
logger = logging.getLogger(__name__)


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_entities(
    # Main search parameters (one is required)
    q: Optional[str] = Query(None, min_length=2, description="Business name search term"),
    sos_id: Optional[str] = Query(None, description="Secretary of State/Entity ID"),
    person_first_name: Optional[str] = Query(None, description="Person's first name to search for"),
    person_last_name: Optional[str] = Query(None, description="Person's last name to search for"),
    retry_id: Optional[str] = Query(None, description="ID for checking status of long-running requests"),
    
    # Required unless using retry_id
    state: Optional[str] = Query(
        None,
        description="State code (required unless using retry_id)"
    ),
    
    # Optional filters
    street: Optional[str] = Query(None, description="Street address to filter results"),
    city: Optional[str] = Query(None, description="City to filter results"),
    zip_code: Optional[str] = Query(None, description="ZIP code to filter results"),
    
    # Data options
    live_data: bool = Query(True, description="Whether to get live data (true) or cached data (false)"),
    include_screenshot: bool = Query(False, description="Whether to include screenshots in results"),
    include_ucc_data: bool = Query(False, description="Whether to include UCC (lien) data in results"),
    
    # Dependencies
    pm: PortfolioManager = Depends(get_portfolio),
    scraper: CobaltScraper = Depends(get_cobalt_scraper),
):
    """
    Search for business entities using Cobalt Intelligence API.
    
    - Search by business name, SoS ID, person name, or retry ID
    - State code is required unless using retry ID
    - Optional address filters (street, city, zip)
    - Option to include screenshots and UCC data
    
    Returns a list of matching entities with normalized data structure.
    """
    # Validate that at least one search parameter is provided
    if not any([q, sos_id, (person_first_name and person_last_name), retry_id]):
        raise HTTPException(
            status_code=400, 
            detail="At least one search parameter is required: q, sos_id, or person_first_name + person_last_name, or retry_id"
        )
    
    # Validate that state is provided unless using retry_id
    if not state and not retry_id:
        raise HTTPException(
            status_code=400,
            detail="State parameter is required unless using retry_id"
        )
    
    search_type = q or sos_id or f"{person_first_name} {person_last_name}" or retry_id
    logger.info(f"Searching Cobalt Intelligence for '{search_type}' in {state or 'based on retry_id'}")
    
    try:
        # Search for entities using the Cobalt scraper with all parameters
        entities = await scraper.search(
            name=q,
            state=state,
            sos_id=sos_id,
            person_first_name=person_first_name,
            person_last_name=person_last_name,
            retry_id=retry_id,
            street=street,
            city=city,
            zip_code=zip_code,
            live_data=live_data,
            include_screenshot=include_screenshot,
            include_ucc_data=include_ucc_data
        )
        
        if not entities:
            logger.warning(f"No entities found for search: '{search_type}'")
            return []
        
        # Add entities to portfolio for persistence
        for entity in entities:
            pm.add(entity)
        
        # Return normalized entity data
        return [_normalize_entity_to_dict(entity) for entity in entities]
    
    except Exception as e:
        logger.error(f"Error searching Cobalt Intelligence API: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching Cobalt Intelligence API: {str(e)}")


@router.get("/details", response_model=Dict[str, Any])
async def get_entity_details(
    name: str = Query(..., min_length=2, description="Business name"),
    state: str = Query(..., min_length=2, max_length=2, description="State code"),
    pm: PortfolioManager = Depends(get_portfolio),
    scraper: CobaltScraper = Depends(get_cobalt_scraper),
):
    """
    Get detailed information for a specific business entity.
    
    Args:
        name: Business name
        state: State code where the business is registered
        
    Returns:
        Normalized business entity data
    """
    logger.info(f"Fetching details for '{name}' in {state}")
    
    try:
        # Fetch entity details
        entity = await scraper.get_details(name, state)
        
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity details not found for '{name}' in {state}")
        
        # Add entity to portfolio for persistence
        pm.add(entity)
        
        # Return normalized entity data
        return _normalize_entity_to_dict(entity)
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error fetching entity details: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching entity details: {str(e)}")


def _normalize_entity_to_dict(entity: CorporateEntity) -> Dict[str, Any]:
    """
    Convert a CorporateEntity to a dictionary for API responses.
    
    Args:
        entity: CorporateEntity object
        
    Returns:
        Dictionary with normalized entity data
    """
    slug = entity.name.lower().replace(" ", "-")
    
    return {
        "slug": slug,
        "name": entity.name,
        "jurisdiction": entity.jurisdiction,
        "status": entity.status.name,
        "formed": entity.formed.isoformat() if entity.formed else None,
        "officers": entity.officers,
        "notes": entity.notes
    }