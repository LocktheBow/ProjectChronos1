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


@dataclass
class CorporateEntity:
    """
    Core record used by Project Chronos.

    Parameters
    ----------
    name : str
        Legal name of the entity.
    jurisdiction : str
        US state or country of formation.
    formed : datetime.date
        Formation date.
    officers : list[str]
        Optional list of officer / manager names.
    status : Status
        Current life‑cycle phase (defaults to PENDING).
    notes : str | None
        Free‑text notes.
    """
    name: str
    jurisdiction: str
    formed: date
    officers: List[str] = field(default_factory=list)
    status: Status = Status.PENDING
    notes: Optional[str] = None
