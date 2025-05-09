

"""
tests/test_portfolio_db.py
==========================

Integration‑style tests for the SQLite‑backed portfolio manager.

These tests mirror `test_portfolio.py` but use DBPortfolioManager to
ensure persistence and API parity with the in‑memory version.
"""

from datetime import date

from chronos.db import create_all
from chronos.models import CorporateEntity, Status
from chronos.portfolio_db import DBPortfolioManager


# ---------------------------------------------------------------------------
# Module‑level setup: ensure fresh schema before tests run
# ---------------------------------------------------------------------------
def setup_module(module):  # noqa: D401
    """(pytest) Create tables once for this test file."""
    create_all()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_add_and_find_by_status():
    pm = DBPortfolioManager()
    ent = CorporateEntity("Beta LLC", "DE", date(2024, 5, 1))
    pm.add(ent)

    pending = pm.find_by_status(Status.PENDING)
    assert pending == [ent]


def test_persistence_across_sessions():
    slug = "gamma-llc"
    ent = CorporateEntity("Gamma LLC", "DE", date(2024, 6, 1))

    # write in first session
    with DBPortfolioManager() as pm:
        pm.add(ent)

    # read in a brand‑new session
    with DBPortfolioManager() as pm2:
        fetched = pm2.get(slug)

    assert fetched.name == "Gamma LLC"
    assert fetched.status == Status.PENDING