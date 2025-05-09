"""
chronos.scrapers.de
===================

Prototype scraper for the Delaware Secretary‑of‑State site.

For classroom use we avoid the live captcha by parsing a static HTML file
saved at ``static-assets/demo_de.html``.  The scraper exposes a single
``fetch(name)`` method that returns a :class:`chronos.models.CorporateEntity`
or ``None`` if the company is not found in the demo file.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

from chronos.models import CorporateEntity, Status
from .base import SoSScraper

# Try to find the HTML next to where the app is launched (project root during dev)
_CWD_DEMO = Path("static-assets/demo_de.html")
if _CWD_DEMO.exists():
    _DEMO_HTML = _CWD_DEMO
else:
    # Fallback: resolve two levels up from this file ( …/chronos/ → project root )
    _DEMO_HTML = Path(__file__).resolve().parents[2] / "static-assets" / "demo_de.html"


class DelawareScraper(SoSScraper):
    """Minimal parser against the demo HTML file."""

    jurisdiction: str = "DE"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch(self, name: str) -> CorporateEntity | None:
        """
        Return a :class:`~chronos.models.CorporateEntity` whose table‑row text
        contains *name* (case‑insensitive).  The demo HTML must include a
        `<tr>` like::

            <tr>
              <td>Foo LLC</td>
              <td>1234567</td>
              <td>01/01/2024</td>
              <td>Active</td>
            </tr>

        ``None`` is returned if no matching row is found.
        """
        if not _DEMO_HTML.exists():
            raise RuntimeError(
                f"Demo HTML not found at {_DEMO_HTML!s} — "
                "the real DE site requires a captcha."
            )

        html = _DEMO_HTML.read_text(encoding="utf‑8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")

        # Normalise whitespace for robust matching
        def _norm(text: str) -> str:
            return " ".join(text.lower().split())  # collapse all whitespace

        q_norm = _norm(name)

        # DEBUG: show all rows for troubleshooting
        print("DEBUG rows seen by scraper ->", [
            _norm(tr.get_text(" ", strip=True)) for tr in soup.find_all("tr")
        ])
        row = next(
            (
                tr
                for tr in soup.find_all("tr")
                if q_norm in _norm(tr.get_text(" ", strip=True))
            ),
            None,
        )
        if row is None:
            return None

        cells = [td.get_text(strip=True) for td in row.find_all("td")]

        # Expected order: [Entity Name, File No, Date Formed, Status, ...]
        try:
            formed = date.fromisoformat(cells[2].replace("/", "-"))
        except (IndexError, ValueError):
            formed = date.today()

        status_text = cells[3].lower() if len(cells) > 3 else ""
        status = Status.ACTIVE if "active" in status_text else Status.DELINQUENT

        return CorporateEntity(
            name=cells[0],
            jurisdiction="DE",
            formed=formed,
            status=status,
        )