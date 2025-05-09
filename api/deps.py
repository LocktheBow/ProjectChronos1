"""
api.deps
========

FastAPI dependency providers.

`get_portfolio` now returns a fresh **DBPortfolioManager** so every
request talks to the persistent SQLite store instead of the in‑memory
PortfolioManager.
"""

from functools import lru_cache

from chronos.portfolio_db import DBPortfolioManager


@lru_cache
def get_portfolio() -> DBPortfolioManager:
    """Singleton DB‑backed portfolio manager (persists across requests)."""
    return DBPortfolioManager()