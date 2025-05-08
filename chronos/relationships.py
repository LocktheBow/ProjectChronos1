"""
chronos.relationships
=====================

Parent → subsidiary ownership graph built on NetworkX.
"""

from __future__ import annotations
import networkx as nx


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
        self.g.add_edge(parent, child, pct=pct)

    def subsidiaries(self, parent: str):
        """Return a list of direct subsidiaries for *parent*."""
        return list(self.g.successors(parent))

    def ownership_pct(self, parent: str, child: str) -> float:
        """Return the stored percentage or raise KeyError if edge missing."""
        return self.g.edges[parent, child]["pct"]
