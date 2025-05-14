"""
API endpoint to get a complete list of entities.

This provides a simple endpoint to retrieve all entities in the portfolio,
which is useful for the relationship form to show all available entities.
"""

from fastapi import APIRouter, Depends
from typing import List, Dict, Any

from chronos.portfolio_db import DBPortfolioManager
from api.deps import get_portfolio

router = APIRouter()

@router.get("/entities/all", response_model=List[Dict[str, Any]])
async def get_all_entities(
    pm: DBPortfolioManager = Depends(get_portfolio)
):
    """
    Get a complete list of all entities in the portfolio.
    
    This is useful for UI elements that need to show all entities,
    such as dropdown selections.
    """
    entities = []
    
    for entity in pm:
        slug = entity.name.lower().replace(" ", "-")
        entities.append({
            "slug": slug,
            "name": entity.name,
            "jurisdiction": entity.jurisdiction,
            "status": entity.status.name,
            "formed": entity.formed.isoformat() if entity.formed else None
        })
    
    return entities