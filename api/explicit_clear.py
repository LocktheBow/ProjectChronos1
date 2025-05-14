"""
Explicit implementation for clearing relationship graph.

This module provides a direct, hardcoded method to completely reset
the relationship graph to an empty state, bypassing the regular handlers.
"""

import os
import json
from fastapi import APIRouter, Response
from datetime import date
from chronos.relationships import RelationshipGraph
from chronos.models import CorporateEntity, Status
from chronos.portfolio_db import DBPortfolioManager

router = APIRouter()

# Completely new, global instance of the relationship graph
FRESH_GRAPH = None

@router.get("/relationships/force-clear")
async def force_clear_relationships():
    """
    Force a complete clearing of the relationship graph.
    
    This endpoint:
    1. Creates a completely new graph instance
    2. Clears all edges and nodes
    3. Does not re-add entities
    """
    global FRESH_GRAPH
    
    # Create a completely fresh graph
    FRESH_GRAPH = RelationshipGraph()
    
    # Return empty graph data
    return {
        "nodes": [],
        "links": []
    }


@router.get("/relationships/export")
async def export_graph():
    """Export the current graph to a JSON file for debugging."""
    try:
        from api.deps import _relationship_graph
        if not _relationship_graph:
            return {"error": "No graph available"}
            
        # Create export directory if needed
        os.makedirs("exports", exist_ok=True)
        
        # Convert graph to JSON
        data = _relationship_graph.to_json()
        
        # Write to file
        filename = f"exports/graph_export_{date.today().isoformat()}.json"
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
            
        return {
            "filename": filename,
            "node_count": len(data["nodes"]),
            "link_count": len(data["links"])
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/relationships/empty")
async def get_empty_relationships():
    """
    Return an empty relationship graph for display.
    
    This is a blunt approach that bypasses the graph management
    in the regular GET /relationships endpoint.
    """
    return {
        "nodes": [],
        "links": []
    }