

"""
chronos.models
==============

Dataclasses and enums representing a single corporate entity and its
life‑cycle status.  These objects are intentionally lightweight; they
carry **no** external‑library dependencies so that importing `chronos`
stays fast even in constrained environments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum, auto
from typing import List, Optional


class Status(Enum):
    """Legal life‑cycle states for a corporate entity."""
    PENDING = auto()
    ACTIVE = auto()
    IN_COMPLIANCE = auto()
    DELINQUENT = auto()
    DISSOLVED = auto()

    def __str__(self) -> str:        # nicer REPL display
        return self.name


@dataclass
class CorporateEntity:
    """
    Core record tracked by Project Chronos.

    Parameters
    ----------
    name : str
        Legal name of the entity (e.g., "ACME LLC").
    jurisdiction : str
        State or country of formation (ISO‑3166 or USPS abbrev).
    formed : datetime.date
        Date the entity was formed.
    officers : list[str], default=[]
        Optional list of officer / manager names.
    status : Status, default=PENDING
        Current life‑cycle phase.
    notes : str | None, default=None
        Free‑text notes (board resolutions, reminders, etc.).
    """
    name: str
    jurisdiction: str
    formed: date
    officers: List[str] = field(default_factory=list)
    status: Status = Status.PENDING
    notes: Optional[str] = None

    # Convenience helpers -------------------------------------------------
    def age_in_days(self, today: Optional[date] = None) -> int:
        """Return entity age in days."""
        today = today or date.today()
        return (today - self.formed).days

    def __post_init__(self):
        if self.formed > date.today():
            raise ValueError("formed date cannot be in the future")