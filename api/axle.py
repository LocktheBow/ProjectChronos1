"""
api.axle
=======

FastAPI router for Data Axle API integration.

This module implements endpoints for searching business entities using the
Data Axle Platform API and retrieving enriched entity data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from httpx import AsyncClient

from chronos.models import CorporateEntity
from chronos.portfolio import PortfolioManager
from chronos.scrapers.axle import DataAxleScraper
from chronos.scrapers.edgar import EdgarClient
from chronos.settings import settings
from .deps import get_portfolio, get_data_axle, get_edgar_client

# Create router
router = APIRouter(prefix="/axle", tags=["axle"])

# Check if EDGAR enrichment is enabled
ENABLE_EDGAR = settings.sec_ua_email and getattr(settings, "enable_edgar", True)


def normalize_entity_to_dict(entity: CorporateEntity) -> Dict[str, Any]:
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


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_entities(
    q: str = Query(..., min_length=2, description="Business name search term"),
    state: Optional[str] = Query(
        None,
        description="Optional two-letter state code filter"
    ),
    axle_client: AsyncClient = Depends(get_data_axle),
    edgar_client: AsyncClient = Depends(get_edgar_client),
    pm: PortfolioManager = Depends(get_portfolio),
):
    """
    Search for business entities using Data Axle API.
    
    - Accepts a company name query (`q`) and optional state code filter
    - Searches Data Axle API and returns normalized results
    - Optionally enriches results with SEC EDGAR data if enabled
    - Adds entities to portfolio for persistence
    
    Returns a list of matching entities with normalized data structure.
    """
    # Create Data Axle scraper
    scraper = DataAxleScraper(axle_client)
    
    # Search for entities
    entities = await scraper.search(q, state=state)
    
    if not entities:
        raise HTTPException(status_code=404, detail="No matching entities found")
    
    # Optionally enrich with EDGAR data
    if ENABLE_EDGAR:
        edgar = EdgarClient(edgar_client)
        enriched_entities = []
        for entity in entities:
            enriched_entity = await edgar.enrich_entity(entity)
            enriched_entities.append(enriched_entity)
        entities = enriched_entities
    
    # Add entities to portfolio for persistence
    for entity in entities:
        pm.add(entity)
    
    # Return normalized entity data
    return [normalize_entity_to_dict(entity) for entity in entities]


@router.get("/entity/{business_id}", response_model=Dict[str, Any])
async def get_entity_by_id(
    business_id: str,
    axle_client: AsyncClient = Depends(get_data_axle),
    edgar_client: AsyncClient = Depends(get_edgar_client),
    pm: PortfolioManager = Depends(get_portfolio),
):
    """
    Fetch a specific business entity by Data Axle ID.
    
    Args:
        business_id: Data Axle business ID
        
    Returns:
        Normalized business entity data
    """
    # Create Data Axle scraper
    scraper = DataAxleScraper(axle_client)
    
    # Fetch entity by ID
    entity = await scraper.fetch_by_id(business_id)
    
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity not found with ID: {business_id}")
    
    # Optionally enrich with EDGAR data
    if ENABLE_EDGAR:
        edgar = EdgarClient(edgar_client)
        entity = await edgar.enrich_entity(entity)
    
    # Add entity to portfolio for persistence
    pm.add(entity)
    
    # Return normalized entity data
    return normalize_entity_to_dict(entity)