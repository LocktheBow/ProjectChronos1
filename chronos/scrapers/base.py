"""
chronos.scrapers.base
=====================

Shared abstract base class for all Secretary‑of‑State scrapers.

Concrete subclasses must implement `.fetch(name: str) -> CorporateEntity | None`.
"""

__all__ = ["SoSScraper", "BaseScraper"]

from abc import ABC, abstractmethod
from chronos.models import CorporateEntity
from chronos.settings import SCRAPER_TIMEOUT, SCRAPER_USER_AGENT

class BaseScraper(ABC):
    """
    Abstract base for all scrapers.

    Concrete subclasses implement API-specific methods.
    """
    
    def __init__(self):
        """Initialize with default settings from configuration."""
        self.timeout = SCRAPER_TIMEOUT
        self.user_agent = SCRAPER_USER_AGENT

class SoSScraper(BaseScraper):
    """
    Abstract base for secretary-of-state scrapers.

    Concrete subclasses implement `.fetch(name:str) -> CorporateEntity | None`.
    """
    
    def __init__(self):
        """Initialize with default settings from configuration."""
        self.timeout = SCRAPER_TIMEOUT
        self.user_agent = SCRAPER_USER_AGENT

    @abstractmethod
    def fetch(self, name: str) -> CorporateEntity | None:
        """Return a CorporateEntity if found, else None."""
        pass