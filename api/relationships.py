"""
api.relationships
===============

Endpoints for managing corporate relationships in the graph.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, List
from pydantic import BaseModel

from chronos.relationships import RelationshipGraph
from chronos.portfolio_db import DBPortfolioManager
from chronos.models import CorporateEntity
from api.deps import _relationship_graph, get_relationships, get_portfolio

router = APIRouter()

class RelationshipRequest(BaseModel):
    """Model for relationship creation request."""
    parent_slug: str
    child_slug: str
    ownership_percentage: float

@router.post("/direct-relationship", status_code=201)
async def create_relationship(
    data: RelationshipRequest,
    rg: RelationshipGraph = Depends(get_relationships),
    pm: DBPortfolioManager = Depends(get_portfolio)
):
    """
    Create a direct parent-child relationship between entities.
    
    This bypasses some validation for testing/demo purposes.
    """
    try:
        # Add nodes if they don't exist
        if data.parent_slug not in rg.g:
            rg.g.add_node(data.parent_slug)
            
        if data.child_slug not in rg.g:
            rg.g.add_node(data.child_slug)
        
        # Create the relationship
        rg.link_parent(
            data.parent_slug,
            data.child_slug,
            data.ownership_percentage
        )
        
        return {
            "status": "success",
            "message": f"Created relationship: {data.parent_slug} → {data.child_slug} ({data.ownership_percentage}%)",
            "total_edges": len(list(rg.g.edges()))
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create relationship: {str(e)}"
        )

@router.post("/clear-all", status_code=200)
async def clear_all_relationships(
    rg: RelationshipGraph = Depends(get_relationships),
    pm: DBPortfolioManager = Depends(get_portfolio)
):
    """
    Clear all relationships in the graph, keeping entities.
    """
    try:
        # Get current edge and node counts for reporting
        edge_count = len(list(rg.g.edges()))
        node_count = len(list(rg.g.nodes()))
        
        # Method 1: Remove all edges one by one
        edges = list(rg.g.edges())
        for source, target in edges:
            rg.g.remove_edge(source, target)
            
        # Verify all edges are removed
        remaining_edges = list(rg.g.edges())
        if remaining_edges:
            # Method 2: Create a new empty graph
            rg.g.clear()
            
            # Re-add all nodes
            for entity in pm:
                slug = entity.name.lower().replace(" ", "-")
                rg.g.add_node(slug)
                rg.add_entity_data(entity)
        
        return {
            "status": "success",
            "message": "All relationships cleared",
            "before": {
                "nodes": node_count,
                "edges": edge_count
            },
            "after": {
                "nodes": len(list(rg.g.nodes())),
                "edges": len(list(rg.g.edges()))
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to clear relationships: {str(e)}"
        )