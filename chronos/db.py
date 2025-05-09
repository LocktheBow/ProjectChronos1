"""
chronos.db
==========

SQLite persistence layer for Project Chronos.

This module exposes:

* ``engine`` – a global SQLModel engine pointing at *chronos.db*
* ``SessionLocal`` – a session factory used via ``with SessionLocal() as s:``
* ``create_all()`` – helper to create tables at first run
"""

from __future__ import annotations

from pathlib import Path
from sqlalchemy import Column, JSON  # new

from sqlmodel import SQLModel, create_engine, Session


# ---------------------------------------------------------------------------
# Engine (SQLite file lives in project root)
# ---------------------------------------------------------------------------
_DB_FILE = Path(__file__).resolve().parents[2] / "chronos.db"
engine = create_engine(f"sqlite:///{_DB_FILE}", echo=False)


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
def SessionLocal() -> Session:  # noqa: N802 (factory camel‑case for consistency with FastAPI docs)
    """Return a new Session bound to the global engine."""
    return Session(engine)


# ---------------------------------------------------------------------------
# ORM model that mirrors chronos.models.CorporateEntity
# ---------------------------------------------------------------------------
from typing import List
from datetime import date
from sqlmodel import Field, JSON, select

from chronos.models import CorporateEntity, Status


class CorporateEntityDB(SQLModel, table=True):
    """
    SQLite‑backed representation of a :class:`chronos.models.CorporateEntity`.

    The primary‑key *slug* is a lower‑cased, dash‑separated version of the
    entity name so look‑ups stay fast and deterministic.
    """

    slug: str = Field(primary_key=True, index=True)
    name: str
    jurisdiction: str
    formed: date
    status: Status = Status.PENDING
    officers: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    notes: str | None = None

    # ---------------------------------------------------------------------
    # Converters
    # ---------------------------------------------------------------------
    @classmethod
    def from_entity(cls, ent: CorporateEntity) -> "CorporateEntityDB":
        """Create a DB row from an in‑memory entity."""
        return cls(
            slug=ent.name.lower().replace(" ", "-"),
            name=ent.name,
            jurisdiction=ent.jurisdiction,
            formed=ent.formed,
            status=ent.status,
            officers=list(ent.officers),
            notes=ent.notes,
        )

    def to_entity(self) -> CorporateEntity:
        """Convert the DB row back into a plain CorporateEntity."""
        return CorporateEntity(
            name=self.name,
            jurisdiction=self.jurisdiction,
            formed=self.formed,
            officers=list(self.officers),
            status=self.status,
            notes=self.notes,
        )


# ---------------------------------------------------------------------------
# Convenience CRUD helpers
# ---------------------------------------------------------------------------
def upsert_entity(s: Session, ent: CorporateEntity) -> None:
    """Insert or update an entity row."""
    row = CorporateEntityDB.from_entity(ent)
    s.merge(row)
    s.commit()


def get_entity(s: Session, slug: str) -> CorporateEntity | None:
    """Return an entity by slug or *None* if missing."""
    db_row = s.get(CorporateEntityDB, slug)
    return db_row.to_entity() if db_row else None


def all_entities(s: Session) -> list[CorporateEntity]:
    """Return every entity in the database."""
    rows = s.exec(select(CorporateEntityDB)).all()
    return [row.to_entity() for row in rows]


# ---------------------------------------------------------------------------
# Utility: create tables
# ---------------------------------------------------------------------------
def create_all() -> None:
    """Create all tables for imported SQLModel subclasses, including CorporateEntityDB."""
    SQLModel.metadata.create_all(engine)

# ---------------------------------------------------------------------------
# Lightweight CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    """
    Quick bootstrap / migration helper.

    Examples
    --------
    $ python -m chronos.db --create        # first‑time table creation
    $ python -m chronos.db --alembic       # run Alembic migrations (if configured)
    """
    import argparse
    import subprocess
    import sys
    import textwrap

    parser = argparse.ArgumentParser(
        prog="python -m chronos.db",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            Chronos DB utilities
            --------------------
            --create   Create all SQLModel tables (safe if they already exist)
            --alembic  Run 'alembic upgrade head' using the project's Alembic 
                       configuration (requires Alembic to be installed).
            """
        ),
    )
    parser.add_argument("--create", action="store_true", help="create tables")
    parser.add_argument("--alembic", action="store_true", help="apply Alembic migrations")
    args = parser.parse_args()

    if args.create:
        create_all()
        print("✅ chronos.db schema initialised")

    if args.alembic:
        exit_code = subprocess.call(["alembic", "upgrade", "head"])
        if exit_code == 0:
            print("✅ Alembic migrations applied")
        sys.exit(exit_code)