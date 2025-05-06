# chronos/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum, auto
from typing import List, Optional


class Status(Enum):
    """Legal life‑cycle states for a corporate entity."""
    PENDING = auto()
    ACTIVE = auto()
    IN_COMPLIANCE = auto()
    DELINQUENT = auto()
    DISSOLVED = auto()


@dataclass
class CorporateEntity:
    """Single company or LLC tracked by Project Chronos."""
    name: str
    jurisdiction: str
    formed: date
    officers: List[str] = field(default_factory=list)
    status: Status = Status.PENDING
    notes: Optional[str] = None

# chronos/portfolio.py
from __future__ import annotations

from typing import Dict, List

from .models import CorporateEntity, Status


class PortfolioManager:
    """
    Registry keyed by slugified company name.

    Acts like a minimal in‑memory database so the rest of Chronos can
    query entities quickly without hitting an external store.
    """

    def __init__(self) -> None:
        self._entities: Dict[str, CorporateEntity] = {}

    # ---------- helpers -------------------------------------------------
    @staticmethod
    def _slug(name: str) -> str:
        return name.lower().replace(" ", "-")

    # ---------- public API ----------------------------------------------
    def add(self, ent: CorporateEntity) -> None:
        """Insert or overwrite a CorporateEntity."""
        self._entities[self._slug(ent.name)] = ent

    def get(self, slug: str) -> CorporateEntity:
        return self._entities[slug]

    def find_by_status(self, status: Status) -> List[CorporateEntity]:
        return [e for e in self._entities.values() if e.status == status]

    # iteration sugar
    def __iter__(self):
        return iter(self._entities.values())

# chronos/relationships.py
import networkx as nx


class RelationshipGraph:
    """
    Directed graph of parent → subsidiary edges.
    Each edge stores the percentage ownership (0–100).
    """

    def __init__(self) -> None:
        self.g = nx.DiGraph()

    def link_parent(self, parent: str, child: str, pct: float) -> None:
        self.g.add_edge(parent, child, pct=pct)

    def subsidiaries(self, parent: str):
        return list(self.g.successors(parent))

# chronos/lifecycle.py
from .models import CorporateEntity, Status

# Legal state‑machine: source -> allowed targets
RULES = {
    Status.PENDING:       {Status.ACTIVE},
    Status.ACTIVE:        {Status.IN_COMPLIANCE, Status.DELINQUENT},
    Status.DELINQUENT:    {Status.IN_COMPLIANCE, Status.DISSOLVED},
    Status.IN_COMPLIANCE: {Status.DELINQUENT,    Status.DISSOLVED},
}


def advance_status(ent: CorporateEntity, new: Status) -> None:
    """Change status if transition is legal, else raise ValueError."""
    if new not in RULES[ent.status]:
        raise ValueError(f"illegal transition {ent.status.name} → {new.name}")
    ent.status = new

# chronos/viz.py
"""
Lightweight plotting helpers – no heavy imports in __init__.
"""
import matplotlib.pyplot as plt
import networkx as nx
from collections import Counter

from .portfolio import PortfolioManager
from .relationships import RelationshipGraph
from .models import Status


def status_summary(pm: PortfolioManager, out_path="images/status_snapshot.png"):
    """
    Bar chart of counts per Status.
    Saves PNG to *images* folder.
    """
    counts = Counter(e.status for e in pm)
    xs, ys = zip(*sorted(counts.items(), key=lambda t: t[0].value))
    plt.figure()
    plt.bar([s.name for s in xs], ys, color="#2b9348")
    plt.title("Status Snapshot")
    plt.ylabel("Entity Count")
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_relationship_graph(rg: RelationshipGraph, out_path="images/ownership_network.png"):
    """Force‑directed graph showing ownership links."""
    plt.figure(figsize=(6, 6))
    pos = nx.spring_layout(rg.g)
    nx.draw_networkx_nodes(rg.g, pos, node_color="#8d99ae", node_size=800)
    nx.draw_networkx_labels(rg.g, pos, font_size=8, font_color="white")
    nx.draw_networkx_edges(rg.g, pos, arrowstyle="->", arrowsize=15)
    edge_labels = nx.get_edge_attributes(rg.g, "pct")
    nx.draw_networkx_edge_labels(rg.g, pos, edge_labels=edge_labels)
    plt.title("Ownership Network")
    plt.axis("off")
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()

# chronos/cli.py
import argparse
import json
from pathlib import Path

from .models import CorporateEntity
from .portfolio import PortfolioManager
from .viz import status_summary


def main():
    parser = argparse.ArgumentParser(description="Chronos CLI demo")
    parser.add_argument("file", help="JSON portfolio dump")
    args = parser.parse_args()

    data = json.loads(Path(args.file).read_text())
    pm = PortfolioManager()
    for record in data:
        pm.add(CorporateEntity(**record))

    status_summary(pm)
    print("status_snapshot.png saved to images/")

# tests/test_models.py
from datetime import date
from chronos.models import CorporateEntity, Status


def test_default_status():
    e = CorporateEntity("Test Inc", "DE", date(2024, 1, 1))
    assert e.status is Status.PENDING

# tests/test_portfolio.py
from datetime import date
from chronos import models, portfolio


def test_add_find():
    pm = portfolio.PortfolioManager()
    ent = models.CorporateEntity("ACME LLC", "DE", date(2024, 5, 1))
    pm.add(ent)
    assert pm.find_by_status(models.Status.PENDING) == [ent]

# tests/test_lifecycle.py
from datetime import date
from chronos.models import CorporateEntity, Status
from chronos.lifecycle import advance_status


def test_good_transition():
    e = CorporateEntity("Foo", "NY", date(2023, 6, 1))
    advance_status(e, Status.ACTIVE)
    assert e.status is Status.ACTIVE


def test_bad_transition():
    e = CorporateEntity("Bar", "NY", date(2023, 6, 1))
    try:
        advance_status(e, Status.DISSOLVED)
    except ValueError:
        assert e.status is Status.PENDING
    else:
        assert False, "should have raised"