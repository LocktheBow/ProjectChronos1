"""
chronos.portfolio_db
====================

SQLite‑backed implementation of the PortfolioManager public surface.

This adapter wraps the CRUD helpers in :pymod:`chronos.db` so that any
code expecting the original in‑memory PortfolioManager can switch to a
persistent store without changing its API calls.
"""

from __future__ import annotations

from typing import Iterator, List

from sqlmodel import Session

from chronos.db import SessionLocal, upsert_entity, get_entity, all_entities
from chronos.models import CorporateEntity, Status


class DBPortfolioManager:
    """
    Drop‑in replacement backed by SQLite.

    Methods mirror the in‑memory PortfolioManager:
    * add(ent)
    * get(slug)
    * find_by_status(status)
    * iteration / len()
    """

    def __init__(self, session: Session | None = None) -> None:
        self._session: Session = session or SessionLocal()

    # ------------------------------------------------------------------ CRUD
    def add(self, ent: CorporateEntity) -> None:
        upsert_entity(self._session, ent)

    def get(self, slug: str) -> CorporateEntity:
        ent = get_entity(self._session, slug)
        if ent is None:
            raise KeyError(slug)
        return ent

    def find_by_status(self, status: Status) -> List[CorporateEntity]:
        return [e for e in all_entities(self._session) if e.status == status]

    # ------------------------------------------------------ dunder helpers
    def __iter__(self) -> Iterator[CorporateEntity]:
        yield from all_entities(self._session)

    def __len__(self) -> int:
        return len(all_entities(self._session))

    # ----------------------------------------------------- context manager
    def __enter__(self) -> "DBPortfolioManager":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._session.close()