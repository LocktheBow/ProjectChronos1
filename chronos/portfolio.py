

"""
chronos.portfolio
=================

An in‑memory registry that stores :class:`chronos.models.CorporateEntity`
objects keyed by a slugified version of their name.

This module is intentionally simple—only the standard library—so that
it can be unit‑tested without external dependencies or a database.
"""

from __future__ import annotations

from typing import Dict, List

from .models import CorporateEntity, Status


class PortfolioManager:
    """
    Dictionary‑backed registry of entities.

    Example
    -------
    >>> from datetime import date
    >>> from chronos.models import CorporateEntity
    >>> pm = PortfolioManager()
    >>> pm.add(CorporateEntity("Foo LLC", "DE", date(2024, 5, 1)))
    >>> list(pm)
    [CorporateEntity(name='Foo LLC', jurisdiction='DE', ...)]
    """

    def __init__(self) -> None:
        self._entities: Dict[str, CorporateEntity] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _slug(name: str) -> str:
        """lower‑cased, dash‑separated key used as unique identifier."""
        return name.lower().replace(" ", "-")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add(self, ent: CorporateEntity) -> None:
        """Insert or overwrite an entity in the portfolio."""
        self._entities[self._slug(ent.name)] = ent

    def get(self, slug: str) -> CorporateEntity:
        """Retrieve by slug (raise KeyError if not present)."""
        return self._entities[slug]

    def find_by_status(self, status: Status) -> List[CorporateEntity]:
        """Return all entities currently at the given Status."""
        return [e for e in self._entities.values() if e.status == status]

    # ------------------------------------------------------------------
    # Dunder helpers for convenience
    # ------------------------------------------------------------------
    def __iter__(self):
        return iter(self._entities.values())

    def __len__(self) -> int:
        return len(self._entities)