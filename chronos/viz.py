"""
chronos.viz
===========

Minimal plotting helpers used by the CLI demo, README screenshots, and
the Jupyter walkthrough notebook.  The module imports *matplotlib* and
*networkx* lazily, so importing `chronos` alone stays lightweight.

Outputs are PNGs written to the *images/* folder (auto‑created if
needed).  Filenames can be overridden via keyword argument.
"""
from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

from .portfolio import PortfolioManager
from .relationships import RelationshipGraph
from .models import Status

# default output dir
_IMG_DIR = Path("images")
_IMG_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------
# Plot 1 – bar chart of entity counts by Status
# ---------------------------------------------------------------------
def status_summary(
    pm: PortfolioManager,
    out_path: str | os.PathLike = _IMG_DIR / "status_snapshot.png",
) -> Path:
    """
    Generate a bar chart of how many entities are in each Status.

    Parameters
    ----------
    pm : PortfolioManager
        The populated portfolio.
    out_path : str or Path, default='images/status_snapshot.png'
        Where to save the PNG.

    Returns
    -------
    pathlib.Path
        Final image path for convenience.
    """
    counts = Counter(ent.status for ent in pm)
    xs, ys = zip(*sorted(counts.items(), key=lambda t: t[0].value))

    plt.figure()
    bars = plt.bar([s.name for s in xs], ys,
                   color="#2b9348", edgecolor="#333")
    # add counts on top of each bar
    for rect, cnt in zip(bars, ys):
        plt.text(rect.get_x() + rect.get_width() / 2,
                 cnt + 0.05,
                 str(cnt),
                 ha="center", va="bottom",
                 fontsize=8, color="#333")
    # subtle y‑axis grid for readability
    plt.grid(axis="y", linestyle=":", alpha=0.3)
    plt.title("Status Snapshot")
    plt.ylabel("Entity Count")
    plt.tight_layout()

    out_path = Path(out_path)
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()
    return out_path


# ---------------------------------------------------------------------
# Plot 2 – force‑directed ownership network graph
# ---------------------------------------------------------------------
def plot_relationship_graph(
    rg: RelationshipGraph,
    out_path: str | os.PathLike = _IMG_DIR / "ownership_network.png",
) -> Path:
    """
    Draw a NetworkX spring‑layout graph of parent → subsidiary links.

    Edge labels show the % ownership stored in :pyclass:`RelationshipGraph`.

    Parameters
    ----------
    rg : RelationshipGraph
        The populated ownership graph.
    out_path : str or Path, default='images/ownership_network.png'
        Where to save the PNG.

    Returns
    -------
    pathlib.Path
        Final image path.
    """
    plt.figure(figsize=(6, 6))
    pos = nx.spring_layout(rg.g, seed=42)

    # nodes
    nx.draw_networkx_nodes(rg.g, pos, node_color="#8d99ae", node_size=800)
    nx.draw_networkx_labels(rg.g, pos, font_size=8, font_color="white")

    # edges + labels
    nx.draw_networkx_edges(rg.g, pos, arrowstyle="->", arrowsize=15)
    edge_labels = nx.get_edge_attributes(rg.g, "pct")
    nx.draw_networkx_edge_labels(rg.g, pos, edge_labels=edge_labels, font_size=7)

    plt.title("Ownership Network")
    plt.axis("off")
    plt.tight_layout()

    out_path = Path(out_path)
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()
    return out_path
#
# ---------------------------------------------------------------------
# CLI demo:  python -m chronos.viz  [--portfolio data.json]
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import json
    from datetime import date

    parser = argparse.ArgumentParser(
        description="Generate status_snapshot.png (and ownership_network.png if relationship data provided).")
    parser.add_argument(
        "--portfolio",
        help="Path to JSON list of CorporateEntity kwargs. If omitted, a demo entity is used.",
    )
    args = parser.parse_args()

    # Build a portfolio manager
    pm = PortfolioManager()
    from pathlib import Path
    from .models import CorporateEntity

    if args.portfolio:
        p = Path(args.portfolio)
        if not p.exists():
            raise SystemExit(f"⛔  File not found: {p!s}")
        data = json.loads(p.read_text())
        from datetime import date
        for rec in data:
            if isinstance(rec.get("formed"), str):
                try:
                    rec["formed"] = date.fromisoformat(rec["formed"])
                except ValueError:
                    raise SystemExit(f"⛔ invalid formed date: {rec['formed']}")
            # convert status string (e.g. "ACTIVE") to Status enum
            if isinstance(rec.get("status"), str):
                try:
                    rec["status"] = Status[rec["status"]]
                except KeyError:
                    raise SystemExit(f"⛔ invalid status: {rec['status']}")
            pm.add(CorporateEntity(**rec))
    else:
        # fallback demo entity
        pm.add(CorporateEntity("DemoCo", "DE", date.today()))

    out = status_summary(pm)
    print(f"status_snapshot saved to {out}")