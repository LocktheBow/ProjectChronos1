from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from chronos.portfolio import PortfolioManager
from chronos.models import CorporateEntity, Status
from fastapi import HTTPException
from fastapi import Query
from typing import Optional, List
from chronos.scrapers.de import DelawareScraper
from .deps import get_portfolio          # <- make sure this import resolves
import os, inspect, chronos.scrapers.de
from pydantic import BaseModel
if os.getenv("SCRAPER_TRACE"):
    print("### Uvicorn imported", inspect.getfile(chronos.scrapers.de))

app = FastAPI(
    title="Project Chronos API",
    version="0.1.0",
    description="HTTP layer over the PortfolioManager.",
)

# --- CORS ----------------------------------------------------------
# During local development the React/Vite front‑end runs on :5173.
# We allow that origin (localhost or 127.0.0.1) to call this API.
# Add more items to *origins* when you deploy (e.g. your production URL).
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- health-check ----------
@app.get("/")
def root():
    return {"status": "ok", "msg": "Chronos API is alive"}

# ---------- POST /entities ----------
@app.post("/entities", status_code=201)
def add_entity(ent: CorporateEntity,
               pm: PortfolioManager = Depends(get_portfolio)):
    pm.add(ent)
    slug = ent.name.lower().replace(" ", "-")
    return {"slug": slug}

# ---------- GET /status ----------
@app.get("/status")
def status_snapshot(pm: PortfolioManager = Depends(get_portfolio)):
    counts: dict[str, int] = {}
    for e in pm:
        counts[e.status.name] = counts.get(e.status.name, 0) + 1
    # ensure zeroes appear
    for s in Status:
        counts.setdefault(s.name, 0)
    return counts

# ---------- GET /entities/{slug} ----------
@app.get("/entities/{slug}", response_model=CorporateEntity)
def get_entity(slug: str, pm: PortfolioManager = Depends(get_portfolio)):
    """
    Return the full CorporateEntity record for a previously‑scraped entity.

    The *slug* is the lower‑cased name with spaces replaced by “-”, exactly
    what /search returns in BusinessSummary.slug. 404 if it is not present in
    the in‑memory PortfolioManager.
    """
    # PortfolioManager may expose .get(), otherwise fall back to linear scan
    ent = getattr(pm, "get", None)
    ent = ent(slug) if callable(ent) else None
    if ent is None:
        for e in pm:
            if e.name.lower().replace(" ", "-") == slug:
                ent = e
                break

    if ent is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    return ent

# ---------- lightweight projection returned by /search ----------
class BusinessSummary(BaseModel):
    slug: str
    name: str
    jurisdiction: str
    status: Status

# ---------- GET /search ----------
@app.get("/search", response_model=list[BusinessSummary])
def search_entities(
    q: str = Query(..., min_length=2, description="Business name search term"),
    state: str | None = Query(
        None,
        min_length=2,
        max_length=2,
        pattern="^[A-Za-z]{2}$",
        description="Optional two‑letter state code",
    ),
    pm: PortfolioManager = Depends(get_portfolio),
):
    """
    Unified business search.

    * For ``state == "DE"`` we hit the internal Delaware demo scraper.
    * Otherwise we search the in‑memory PortfolioManager by case‑insensitive
      substring match on name and optional jurisdiction filter.

    Every hit is added to the portfolio (idempotent) so subsequent
    searches and status snapshots include it.
    """
    matches: list[CorporateEntity] = []

    # -- state‑specific scraper ------------------------------------------------
    if state and state.upper() == "DE":
        record = DelawareScraper().fetch(q)
        if record:
            pm.add(record)
            matches.append(record)

    # -- fallback: search current portfolio -----------------------------------
    q_lower = q.lower()
    for ent in pm:
        print("-- matcher:", q_lower, "vs", ent.name.lower(), flush=True)
        if q_lower in ent.name.lower() and (not state or ent.jurisdiction.upper() == state.upper()):
            matches.append(ent)

    if not matches:
        raise HTTPException(status_code=404, detail="No matching entities found")

    # prepare slim summaries for the client
    summaries = [
        BusinessSummary(
            slug=ent.name.lower().replace(" ", "-"),
            name=ent.name,
            jurisdiction=ent.jurisdiction,
            status=ent.status,
        )
        for ent in matches
    ]
    return summaries

# ---------- GET /sos/de ----------
@app.get("/sos/de")
def sos_de(name: str, pm: PortfolioManager = Depends(get_portfolio)):
    """
    Fetch a Delaware entity from the secretary‑of‑state demo scraper.
    Adds it to the in‑memory portfolio and returns the parsed record.
    """
    scraper = DelawareScraper()
    ent = scraper.fetch(name)
    if ent is None:
        raise HTTPException(status_code=404, detail="Entity not found in Delaware SoS demo")
    pm.add(ent)
    return ent