

"""
Chronos
=======

A lightweight toolkit for modelling, tracking, and visualising the
life‑cycle of corporate entities.

Import structure
----------------
`import chronos` is intentionally cheap: only the stdlib-based
sub‑modules are imported by default.  Heavy dependencies such as
*matplotlib* and *networkx* are only imported when you explicitly
access :pymod:`chronos.viz`.

Sub‑modules
~~~~~~~~~~~
- :pymod:`chronos.models`          – ``CorporateEntity`` dataclass + :class:`~chronos.models.Status` enum
- :pymod:`chronos.portfolio`       – ``PortfolioManager`` in‑memory registry
- :pymod:`chronos.relationships`   – parent → subsidiary graph (NetworkX)
- :pymod:`chronos.lifecycle`       – state‑machine guard (`advance_status`)
- :pymod:`chronos.viz`             – plotting helpers (bar chart + graph)

Quick start
-----------
>>> from datetime import date
>>> from chronos.models import CorporateEntity, Status
>>> from chronos.portfolio import PortfolioManager
>>> ent = CorporateEntity("ACME LLC", "DE", date(2024, 5, 1))
>>> pm = PortfolioManager(); pm.add(ent)
>>> list(pm.find_by_status(Status.PENDING))
[CorporateEntity(name='ACME LLC', jurisdiction='DE', ...)]

"""

__all__ = [
    "models",
    "portfolio",
    "relationships",
    "lifecycle",
    "viz",
]

__version__ = "0.1.0"