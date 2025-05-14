"""
chronos.relationships
=====================

Parent → subsidiary ownership graph built on NetworkX.
"""

from __future__ import annotations
import networkx as nx
from typing import Dict, List, Any, Optional
from .models import CorporateEntity, Status


class RelationshipGraph:
    """
    Lightweight wrapper around a DiGraph that stores % ownership.

    Example
    -------
    >>> rg = RelationshipGraph()
    >>> rg.link_parent("HoldCo", "OpCo1", 100.0)
    >>> rg.link_parent("HoldCo", "OpCo2", 75.0)
    >>> rg.subsidiaries("HoldCo")
    ['OpCo1', 'OpCo2']
    """

    def __init__(self) -> None:
        self.g = nx.DiGraph()
        self._entity_data: Dict[str, Dict[str, Any]] = {}  # Store entity details by slug

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def link_parent(self, parent: str, child: str, pct: float) -> None:
        """
        Add an edge parent → child with a percentage ownership.

        pct is stored as a float (0–100).  If the edge already exists,
        it will be overwritten with the new percentage.
        """
        if not (0.0 <= pct <= 100.0):
            raise ValueError("pct must be between 0 and 100")
            
        # Ensure both nodes exist in the graph before creating edge
        if parent not in self.g:
            self.g.add_node(parent)
            print(f"Adding missing node: {parent}")
            
        if child not in self.g:
            self.g.add_node(child)
            print(f"Adding missing node: {child}")
            
        self.g.add_edge(parent, child, pct=pct)

    def subsidiaries(self, parent: str):
        """Return a list of direct subsidiaries for *parent*."""
        return list(self.g.successors(parent))
    
    def parents(self, child: str):
        """Return a list of direct parents for *child*."""
        return list(self.g.predecessors(child))

    def ownership_pct(self, parent: str, child: str) -> float:
        """Return the stored percentage or raise KeyError if edge missing."""
        return self.g.edges[parent, child]["pct"]
    
    def add_entity_data(self, entity: CorporateEntity) -> None:
        """Add or update entity metadata in the graph."""
        slug = entity.name.lower().replace(" ", "-")
        self._entity_data[slug] = {
            "name": entity.name,
            "jurisdiction": entity.jurisdiction,
            "status": entity.status.name,
            "formed": entity.formed.isoformat() if entity.formed else None,
        }
        # Ensure node exists in graph
        if slug not in self.g:
            self.g.add_node(slug)
    
    def get_entity_data(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get entity metadata by slug."""
        return self._entity_data.get(slug)
    
    def to_json(self) -> Dict[str, Any]:
        """
        Convert the graph to JSON format for visualization.
        Returns a dict with nodes and links arrays.
        """
        nodes = []
        for node in self.g.nodes():
            node_data = self.get_entity_data(node) or {"name": node, "status": "UNKNOWN"}
            nodes.append({
                "id": node,
                "name": node_data.get("name", node),
                "status": node_data.get("status", "UNKNOWN"),
                "jurisdiction": node_data.get("jurisdiction", ""),
                # Calculate node type based on connections
                "type": "PRIMARY" if self.parents(node) == [] else "SUBSIDIARY"
            })
        
        links = []
        for source, target, data in self.g.edges(data=True):
            links.append({
                "source": source,
                "target": target,
                "value": data.get("pct", 0)
            })
        
        return {
            "nodes": nodes,
            "links": links
        }
    
    def identify_proxies(self) -> List[str]:
        """Find entities that appear to be acting as proxies."""
        proxies = []
        for node in self.g.nodes():
            # Entity with multiple parents of similar structure may be a proxy
            if len(list(self.g.predecessors(node))) > 1:
                proxies.append(node)
        return proxies
    
    def identify_shell_companies(self) -> List[Dict[str, Any]]:
        """
        Identify potential shell companies based on graph structure.
        Returns a list of entity slugs with their shell risk score.
        """
        shells = []
        
        for node in self.g.nodes():
            risk_score = 0.0
            entity_data = self.get_entity_data(node)
            
            if not entity_data:
                continue
                
            # Factor 1: No subsidiaries but is owned by others
            if (len(self.subsidiaries(node)) == 0 and 
                len(self.parents(node)) > 0):
                risk_score += 0.3
                
            # Factor 2: Entity is in a chain of single-child owners
            if (len(self.parents(node)) == 1 and 
                len(self.subsidiaries(self.parents(node)[0])) == 1):
                risk_score += 0.2
                
            # Factor 3: Status indicators
            if entity_data.get("status") == "ACTIVE" and len(self.subsidiaries(node)) == 0:
                risk_score += 0.1
                
            if risk_score >= 0.3:  # Threshold for reporting
                shells.append({
                    "slug": node,
                    "name": entity_data.get("name", node),
                    "risk_score": risk_score
                })
                
        return sorted(shells, key=lambda x: x["risk_score"], reverse=True)
