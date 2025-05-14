"""
api.opencorp
===========

FastAPI router for OpenCorporates API integration.

This module implements endpoints for searching business entities using 
OpenCorporates API and retrieving entity data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging
import asyncio
import os

from chronos.models import CorporateEntity
from chronos.portfolio import PortfolioManager
from chronos.scrapers.opencorp import OpenCorporatesScraper
from .deps import get_portfolio, get_opencorp_scraper

# Create router
router = APIRouter(prefix="/opencorp", tags=["opencorp"])

# Configure logging
logger = logging.getLogger(__name__)


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_entities(
    q: str = Query(..., min_length=2, description="Business name search term"),
    state: Optional[str] = Query(
        None,
        description="Optional two-letter state code filter"
    ),
    pm: PortfolioManager = Depends(get_portfolio),
    scraper: OpenCorporatesScraper = Depends(get_opencorp_scraper),
):
    """
    Search for business entities using OpenCorporates API.
    
    - Accepts a company name query (`q`) and optional state code filter
    - Searches OpenCorporates and returns normalized results
    - Adds entities to portfolio for persistence
    
    Returns a list of matching entities with normalized data structure.
    """
    logger.info(f"Searching OpenCorporates for '{q}' in {state or 'all jurisdictions'}")
    
    try:
        # Search for entities using the OpenCorporates scraper
        entities = await scraper.search(q, state)
        
        if not entities:
            logger.warning(f"No entities found for '{q}' in {state or 'all jurisdictions'}")
            return []
        
        # Add entities to portfolio for persistence
        for entity in entities:
            pm.add(entity)
        
        # Return normalized entity data
        return [_normalize_entity_to_dict(entity) for entity in entities]
    
    except Exception as e:
        logger.error(f"Error searching OpenCorporates API: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching OpenCorporates API: {str(e)}")


@router.get("/entity/{jurisdiction}/{company_id}", response_model=Dict[str, Any])
async def get_entity_by_id(
    jurisdiction: str,
    company_id: str,
    pm: PortfolioManager = Depends(get_portfolio),
    scraper: OpenCorporatesScraper = Depends(get_opencorp_scraper),
):
    """
    Fetch a specific business entity by OpenCorporates ID and jurisdiction.
    
    Args:
        jurisdiction: Jurisdiction code (e.g., 'us_de' for Delaware)
        company_id: OpenCorporates company ID
        
    Returns:
        Normalized business entity data
    """
    logger.info(f"Fetching company with ID: {company_id} in {jurisdiction}")
    
    try:
        # Fetch entity by ID and jurisdiction
        entity = await scraper.fetch_by_id(company_id, jurisdiction)
        
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity not found with ID: {company_id} in {jurisdiction}")
        
        # Fetch officers for the entity
        officers = await scraper.fetch_officers(company_id, jurisdiction)
        if officers:
            entity.officers = officers
        
        # Add entity to portfolio for persistence
        pm.add(entity)
        
        # Return normalized entity data
        return _normalize_entity_to_dict(entity)
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error fetching entity: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching entity: {str(e)}")


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