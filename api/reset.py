"""
Reset endpoint for the relationship graph.

This provides a simple API endpoint to completely reset the relationship graph,
which is useful for debugging and for the front-end to reset the graph.
"""

from fastapi import APIRouter, Depends
from chronos.relationships import RelationshipGraph
from chronos.portfolio_db import DBPortfolioManager
from api.deps import _relationship_graph

router = APIRouter()

@router.post("/relationships/reset")
async def reset_graph():
    """
    Completely reset the relationship graph.
    
    This creates a new, empty graph and adds all entities from the portfolio
    to it without any relationships.
    """
    # Create a completely new graph
    fresh_graph = RelationshipGraph()
    
    # Get the portfolio to add all entities
    portfolio = DBPortfolioManager()
    
    # Add all entities but no relationships
    for entity in portfolio:
        fresh_graph.add_entity_data(entity)
    
    # Replace the global graph reference
    global _relationship_graph
    _relationship_graph = fresh_graph
    
    return {
        "status": "success", 
        "message": "Graph reset complete", 
        "nodes": len(fresh_graph.g.nodes()),
        "edges": len(fresh_graph.g.edges())
    }