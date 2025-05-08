"""
chronos.lifecycle
=================

State‑transition guard for a :class:`chronos.models.CorporateEntity`.

A tiny finite‑state‑machine describes which life‑cycle phases are legal
successors of each status.  The helper :pyfunc:`advance_status` mutates
an entity **in‑place** after validating the transition.
"""

from __future__ import annotations

from .models import CorporateEntity, Status

# ---------------------------------------------------------------------
# Allowed transitions: source status → set[valid target statuses]
# ---------------------------------------------------------------------
RULES = {
    Status.PENDING:       {Status.ACTIVE},
    Status.ACTIVE:        {Status.IN_COMPLIANCE, Status.DELINQUENT},
    Status.IN_COMPLIANCE: {Status.DELINQUENT, Status.DISSOLVED},
    Status.DELINQUENT:    {Status.IN_COMPLIANCE, Status.DISSOLVED},
}


def advance_status(entity: CorporateEntity, new_status: Status) -> None:
    """
    Change :pyattr:`entity.status` if the transition is legal,
    otherwise raise :class:`ValueError`.

    Examples
    --------
    >>> e = CorporateEntity("Foo LLC", "DE", date(2023, 1, 1))
    >>> advance_status(e, Status.ACTIVE)
    >>> advance_status(e, Status.DISSOLVED)
    Traceback (most recent call last):
        ...
    ValueError: illegal transition ACTIVE → DISSOLVED
    """
    current = entity.status
    if new_status not in RULES.get(current, set()):
        raise ValueError(f"illegal transition {current.name} → {new_status.name}")
    entity.status = new_status
