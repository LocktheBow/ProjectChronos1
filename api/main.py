from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from chronos.portfolio import PortfolioManager
from chronos.models import CorporateEntity, Status
from fastapi import HTTPException
from chronos.scrapers.de import DelawareScraper
from .deps import get_portfolio          # <- make sure this import resolves
import os, inspect, chronos.scrapers.de
if os.getenv("SCRAPER_TRACE"):
    print("### Uvicorn imported", inspect.getfile(chronos.scrapers.de))

app = FastAPI(
    title="Project Chronos API",
    version="0.1.0",
    description="HTTP layer over the PortfolioManager.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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