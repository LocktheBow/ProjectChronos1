"""
Utility script to reset the relationship graph state.

This script completely clears the relationship graph by:
1. Creating a new, empty RelationshipGraph object
2. Replacing the current in-memory graph
3. Reconnecting basic entity data without relationships

This can be useful when the graph state becomes corrupted or
when you need to start fresh without restarting the server.
"""

from chronos.relationships import RelationshipGraph
from chronos.portfolio import PortfolioManager
from chronos.portfolio_db import DBPortfolioManager
from api.deps import _relationship_graph

def clear_graph():
    """Create a fresh relationship graph and reconnect entities."""
    # Create a fresh graph
    fresh_graph = RelationshipGraph()
    
    # Get access to the portfolio
    portfolio = DBPortfolioManager()
    
    # Add all entities from portfolio to the fresh graph (without relationships)
    for entity in portfolio:
        fresh_graph.add_entity_data(entity)
    
    # Replace the old graph with the fresh one
    global _relationship_graph
    _relationship_graph = fresh_graph
    
    print(f"Graph reset complete. {len(list(fresh_graph.g.nodes()))} nodes added.")
    print(f"No relationships/edges exist in the fresh graph.")
    
    return _relationship_graph

if __name__ == "__main__":
    clear_graph()