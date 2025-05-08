"""
Ensure project root is on sys.path so `import chronos` works during tests.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # tests/.. → project root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
"""
tests/test_models.py
====================

Unit tests for the dataclass and enum defined in chronos.models.

Run:  pytest -q
"""

from datetime import date, timedelta

import pytest

from chronos.models import CorporateEntity, Status


def test_default_status():
    """New entity defaults to PENDING."""
    ent = CorporateEntity("Foo LLC", "DE", date(2024, 5, 1))
    assert ent.status is Status.PENDING


def test_str_on_status():
    """Enum __str__ returns its name (nicer REPL)."""
    assert str(Status.ACTIVE) == "ACTIVE"


def test_age_in_days():
    """age_in_days helper returns positive integer."""
    formed = date.today() - timedelta(days=30)
    ent = CorporateEntity("Bar Inc", "NY", formed)
    assert ent.age_in_days() >= 30


def test_future_formed_date_raises():
    """Formation date in the future should raise."""
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ValueError):
        CorporateEntity("Future LLC", "CA", tomorrow)