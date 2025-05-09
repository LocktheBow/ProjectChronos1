

"""
tests/test_scraper_de.py
========================

Unit test for the Delaware Secretary‑of‑State demo scraper.

It exercises the local *static-assets/demo_de.html* fixture and ensures
that the scraper returns a populated CorporateEntity with ACTIVE status.
"""

from chronos.scrapers.de import DelawareScraper
from chronos.models import Status


def test_fetch_demo_entity():
    """
    The demo HTML contains a row for 'Foo LLC' marked Active.
    The scraper should return a CorporateEntity matching that row.
    """
    scraper = DelawareScraper()
    ent = scraper.fetch("Foo LLC")
    assert ent is not None, "Expected 'Foo LLC' not found in demo file"
    assert ent.name == "Foo LLC"
    assert ent.jurisdiction == "DE"
    assert ent.status == Status.ACTIVE