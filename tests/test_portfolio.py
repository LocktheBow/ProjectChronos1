

"""
tests/test_portfolio.py
=======================

Unit tests for chronos.portfolio.PortfolioManager
"""

from datetime import date

from chronos.models import CorporateEntity, Status
from chronos.portfolio import PortfolioManager


def _demo_portfolio():
    pm = PortfolioManager()
    pm.add(CorporateEntity("Foo LLC", "DE", date(2024, 5, 1)))  # PENDING
    pm.add(CorporateEntity("Bar Inc", "NY", date(2023, 6, 1), status=Status.ACTIVE))
    pm.add(CorporateEntity("Baz GmbH", "DE", date(2022, 1, 15), status=Status.DELINQUENT))
    return pm


def test_add_and_get_by_slug():
    pm = PortfolioManager()
    ent = CorporateEntity("Acme Corp", "CA", date(2024, 4, 1))
    pm.add(ent)
    assert pm.get("acme-corp") is ent


def test_find_by_status():
    pm = _demo_portfolio()
    delinquent = pm.find_by_status(Status.DELINQUENT)
    assert len(delinquent) == 1
    assert delinquent[0].name == "Baz GmbH"


def test_len_and_iter():
    pm = _demo_portfolio()
    assert len(pm) == 3
    names = {e.name for e in pm}
    assert names == {"Foo LLC", "Bar Inc", "Baz GmbH"}