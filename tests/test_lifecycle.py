"""
Pytest configuration: make sure `import chronos` works regardless of
where pytest is invoked.

It prepends the project root (one directory above *tests/*) to
``sys.path`` **before** any tests are collected.
"""

import sys
from pathlib import Path

# /path/to/project/tests -> project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

"""
tests/test_lifecycle.py
=======================

Unit tests for chronos.lifecycle.advance_status
"""

from datetime import date

import pytest

from chronos.lifecycle import advance_status
from chronos.models import CorporateEntity, Status


def test_good_transition():
    """ACTIVE → IN_COMPLIANCE should succeed."""
    ent = CorporateEntity("Foo LLC", "DE", date(2024, 1, 1), status=Status.ACTIVE)
    advance_status(ent, Status.IN_COMPLIANCE)
    assert ent.status is Status.IN_COMPLIANCE


def test_illegal_transition_raises():
    """ACTIVE → DISSOLVED is not allowed and should raise ValueError."""
    ent = CorporateEntity("Bar Inc", "NY", date(2023, 6, 1), status=Status.ACTIVE)
    with pytest.raises(ValueError):
        advance_status(ent, Status.DISSOLVED)