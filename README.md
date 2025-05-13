## 🚀 Project Roadmap

| Phase | Target Date | Description | Status |
|-------|-------------|-------------|--------|
| 1. Repository Skeleton | **DONE** | Folders, stub modules, CI skeleton | ✅ Complete |
| 2. Core Data Models | Day 0 – Day 1 | `CorporateEntity`, `Status`, unit tests | ✅ Complete |
| 3. Portfolio & Relationships | Day 1 – Day 2 | `PortfolioManager`, `RelationshipGraph` + tests | ✅ Complete |
| 4. Lifecycle Engine | Day 2 | State‑machine guards & tests | ✅ Complete |
| 5. Visualization Layer | Day 3 | Bar chart + ownership graph (MVP) | ✅ **MVP delivered** |
| 6. CLI Demo & Sample Data | Day 4 | `python -m chronos.cli sample.json` | 🟢 In Progress |
| 7. Docs & Notebook | Day 5 | Filled README, demo notebook screenshots | 🟡 Drafting |
| 8. Test Coverage ≥ 90 % | Day 6 | 9 core tests pass, coverage rising | 🟢 In Progress |
| 9. Polishing & Packaging | Day 7 | Type hints, docstrings, `pip install .` | ⏳ Pending |
| 10. Final Tag `v1.0-final` | **May 14 09:00** | Freeze code, hand‑in | ⏳ Pending |

## ✅ Requirements Compliance Tracker

- [x] **Proposal submitted** (initial & final) citeturn4file0
- [x] **Python chosen as primary language**
- [x] **GitHub repo with regular commits**
- [x] **Core data‑structures implemented & tested**
- [x] **CLI demo renders `status_snapshot.png`**
- [x] **FastAPI backend (`/entities`, `/status`, `/sosearch`) live**
- [x] **React + Tailwind UI prototype (search + chart)**
- [x] **Visualization of relationships & status**
- [x] **50‑state scraper layer via OpenCorporates API integration**
- [x] **EDGAR integration for SEC filing enrichment**
- [ ] Full test coverage ≥ 90 %
- [ ] Docker compose one‑click stack
- [ ] Live demo content & slides

## 🔭 Next Steps (rolling 48 h)

- **Front‑end polish** – Tailwind styling, loading states, bind live `/status` counts.
- **API token setup** – add instructions for setting up OpenCorporates and SEC accounts.
- **Docs refresh** – embed updated UI screenshots & quick‑start commands.

---

## 🛠️ OpenCorporates & EDGAR Integration

The project now uses the OpenCorporates API to provide comprehensive business entity data
across all 50 US states and international jurisdictions, along with optional SEC EDGAR enrichment.

### OpenCorporates Configuration

To use the OpenCorporates API integration:

1. Sign up for an API key at [OpenCorporates](https://opencorporates.com/api_accounts/new)
2. Set the API key as an environment variable:
   ```
   export OPENCORP_API_TOKEN=your-api-token
   ```

### SEC EDGAR Configuration

To enable SEC EDGAR enrichment:

1. Enable the EDGAR integration with an environment variable:
   ```
   export ENABLE_EDGAR=true
   ```
2. Optionally set a descriptive User-Agent to identify your application to the SEC:
   ```
   export EDGAR_USER_AGENT="Your Company Name (contact@example.com)"
   ```

### Rate Limits & Caching

- OpenCorporates free tier is limited to 10 requests per hour
- All API responses are cached for 24 hours to minimize API calls
- The cache is stored in SQLite at `./chronos_cache.db` by default
- Set a custom cache directory with `CHRONOS_CACHE_DIR` environment variable

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
| **B** | 50‑State scraper layer | `chronos/scrapers/openc.py` – OpenCorporates API integration for all 50 states, inheriting from `BaseScraper`; responses cached in SQLite |
| **C** | EDGAR integration | `chronos/scrapers/edgar.py` – SEC EDGAR API integration for enriching entities with CIK numbers and latest filing URLs |
| **D** | React/Tailwind front‑end | `ui/` folder (Vite app) with: <br>• Search bar (unified SoS + EDGAR) <br>• Status snapshot card <br>• Ownership network D3 panel |
| **E** | Auth & multi‑portfolio | Simple OAuth (GitHub / Google) → each user sees only their saved portfolios |
| **F** | Docker compose | `docker-compose.yml` spins up API, worker, and UI so graders run `docker compose up` and get the full stack |
| **G** | One‑click deploy | Render .com or Fly.io blueprint + GitHub Action (`on: push`) that builds & deploys main branch |

> **Current position:** Stages **A**, **B**, and **C** are completed. Core Python
> data‑models now power the API, with OpenCorporates API integration for entity lookup
> across all jurisdictions and EDGAR integration for SEC filing information.
> The React UI is connected to the API endpoints for searching and visualization.

Use this table as the guiding checklist before touching code for the web
phase. Feel free to modify priorities or swap hosting targets as team
preferences evolve.