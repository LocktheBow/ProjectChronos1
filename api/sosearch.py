"""
api.sosearch
==========

FastAPI endpoint for unified Secretary of State search using OpenCorporates.

This module implements the `/sosearch` endpoint that provides a simplified
interface to search for corporate entities across multiple jurisdictions
using the OpenCorporates API, with optional SEC EDGAR enrichment.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import os

from chronos.scrapers.openc import OpenCorporatesScraper
from chronos.scrapers.edgar import EdgarClient
from chronos.models import CorporateEntity, Status
from chronos.portfolio import PortfolioManager
from .deps import get_portfolio

# Create router
router = APIRouter(tags=["sosearch"])

# Check if EDGAR enrichment is enabled
ENABLE_EDGAR = os.environ.get("ENABLE_EDGAR", "false").lower() in ("true", "1", "yes")


class BusinessSummary:
    """Business summary model returned by search endpoints"""
    slug: str
    name: str
    jurisdiction: str
    status: Status


def normalize_entity_to_summary(entity: CorporateEntity) -> Dict[str, Any]:
    """
    Convert a CorporateEntity to a summary dictionary for API responses.
    
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
    }


@router.get("/sosearch", response_model=List[Dict[str, Any]])
async def search_entities(
    q: str = Query(..., min_length=2, description="Business name search term"),
    jurisdiction: Optional[str] = Query(
        None,
        description="Optional jurisdiction code (two-letter state code or 'all')"
    ),
    pm: PortfolioManager = Depends(get_portfolio),
):
    """
    Search for business entities using OpenCorporates API.
    
    - Accepts a company name query (`q`) and optional jurisdiction filter
    - Searches OpenCorporates API and returns normalized results
    - Caches results for 24 hours to reduce API calls
    - Optionally enriches results with SEC EDGAR data if enabled
    
    Returns a list of matching entities with normalized data structure.
    """
    # Create scraper instances
    scraper = OpenCorporatesScraper()
    
    # If jurisdiction is "all" or None, search globally
    search_jurisdiction = None
    if jurisdiction and jurisdiction.lower() != "all":
        search_jurisdiction = jurisdiction
    
    # Search for entities
    entities = scraper.search(q, jurisdiction=search_jurisdiction)
    
    if not entities:
        raise HTTPException(status_code=404, detail="No matching entities found")
    
    # Optionally enrich with EDGAR data
    if ENABLE_EDGAR:
        edgar_client = EdgarClient()
        entities = [edgar_client.enrich_entity(entity) for entity in entities]
    
    # Add entities to portfolio for persistence
    for entity in entities:
        pm.add(entity)
    
    # Return normalized entity summaries
    return [normalize_entity_to_summary(entity) for entity in entities]


@router.get("/sosearch/{jurisdiction}/{company_number}", response_model=Dict[str, Any])
async def get_entity_by_id(
    jurisdiction: str,
    company_number: str,
    pm: PortfolioManager = Depends(get_portfolio),
):
    """
    Fetch a specific company by its jurisdiction and company number.
    
    Args:
        jurisdiction: Two-letter jurisdiction code
        company_number: Company registration number
        
    Returns:
        Normalized company data
    """
    # Create scraper instance
    scraper = OpenCorporatesScraper()
    
    # Fetch entity by ID
    entity = scraper.fetch_by_id(company_number, jurisdiction)
    
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity not found: {company_number} in {jurisdiction}")
    
    # Optionally enrich with EDGAR data
    if ENABLE_EDGAR:
        edgar_client = EdgarClient()
        entity = edgar_client.enrich_entity(entity)
    
    # Add entity to portfolio for persistence
    pm.add(entity)
    
    # Return normalized entity data
    return normalize_entity_to_summary(entity)