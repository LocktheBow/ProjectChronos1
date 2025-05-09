## 🚀 Project Roadmap

| Phase | Target Date | Description | Status |
|-------|-------------|-------------|--------|
| 1. Repository Skeleton | **DONE** | Create folders, stub modules, tests, CI skeleton | ✅ Complete |
| 2. Core Data Models | Day 0 – Day 1 | Implement `CorporateEntity`, `Status`, unit tests | ✅ Complete |
| 3. Portfolio & Relationships | Day 1 – Day 2 | Finish `PortfolioManager`, `RelationshipGraph` logic + tests | 🟢 In Progress (code drafted) |
| 4. Lifecycle Engine | Day 2 | Validate state‑machine transitions, raise on illegal moves | ✅ Complete |
| 5. Visualization Layer | Day 3 | Bar‑chart + ownership graph saved to `images/` | 🟡 Stub created, plotting TBD |
| 6. CLI Demo & Sample Data | Day 4 | One‑command demo: `python -m chronos.cli sample.json` | ⏳ Pending |
| 7. Docs & Notebook Walkthrough | Day 5 | Fill README, add `notebook_demo.ipynb` screenshots | ⏳ Pending |
| 8. Full Test Coverage & CI badge | Day 6 | 90% pytest coverage, GitHub Actions workflow | ⏳ Pending |
| 9. Polishing & Packaging | Day 7 | Type hints, docstrings, `pip install .` ready | ⏳ Pending |
| 10. Final Tag `v1.0-final` | May 14 09:00 | Freeze code, hand in | ⏳ Pending |

**Current position:** We’re midway through **Phase 3**. Core classes compile, first tests pass.  
Next immediate task is to flesh out plotting logic in `chronos/viz.py` and commit `sample_portfolio.json` so the CLI demo renders `status_snapshot.png`.

---
# ProjectChronos1

---

## 🌐 Web Interface & 50‑State Search Roadmap

The high‑level path to evolve Chronos from a CLI toolkit into a
browser‑based dashboard that pulls Secretary‑of‑State data from all 50
U.S. jurisdictions *plus* SEC EDGAR filings.

| Stage | Milestone | Concrete Deliverable |
|-------|-----------|----------------------|
| **A** | REST API surface | `api/` FastAPI app exposing `/entities`, `/status`, `/relationships`, `/sosearch?state=DE&query=acme` |
| **B** | 50‑State scraper layer | `chronos/scrapers/` – one module per state, all inheriting a common `BaseScraper`; nightly cron populates SQLite |
| **C** | EDGAR integration | Call SEC’s full‑text search endpoint → store CIK + latest Filing URL in `edgar_filings` table |
| **D** | React/Tailwind front‑end | `ui/` folder (Vite app) with: <br>• Search bar (unified SoS + EDGAR) <br>• Status snapshot card <br>• Ownership network D3 panel |
| **E** | Auth & multi‑portfolio | Simple OAuth (GitHub / Google) → each user sees only their saved portfolios |
| **F** | Docker compose | `docker-compose.yml` spins up API, worker, and UI so graders run `docker compose up` and get the full stack |
| **G** | One‑click deploy | Render .com or Fly.io blueprint + GitHub Action (`on: push`) that builds & deploys main branch |

> **Current position:** Stages **A** & **B** are next. Core Python
> data‑models already power the API, so we’ll scaffold FastAPI then add
> one or two scraper prototypes (e.g. Delaware & California).  
> Once those endpoints stabilise, we’ll plug the React UI into the API
> and iterate.

Use this table as the guiding checklist before touching code for the web
phase. Feel free to modify priorities or swap hosting targets as team
preferences evolve.
