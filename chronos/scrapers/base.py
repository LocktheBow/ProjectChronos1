"""
chronos.scrapers.base
=====================

Shared abstract base class for all Secretary‑of‑State scrapers.

Concrete subclasses must implement `.fetch(name: str) -> CorporateEntity | None`.
"""

__all__ = ["SoSScraper"]

from abc import ABC, abstractmethod
from chronos.models import CorporateEntity

class SoSScraper(ABC):
    """
    Abstract base for secretary-of-state scrapers.

    Concrete subclasses implement `.fetch(name:str) -> CorporateEntity | None`.
    """

    @abstractmethod
    def fetch(self, name: str) -> CorporateEntity | None:
        """Return a CorporateEntity if found, else None."""
        pass