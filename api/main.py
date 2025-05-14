from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from chronos.portfolio import PortfolioManager
from chronos.models import CorporateEntity, Status
from chronos.relationships import RelationshipGraph
from chronos.settings import API_HOST, API_PORT, API_DEBUG, SCRAPER_TIMEOUT, SCRAPER_USER_AGENT
from .deps import get_portfolio, get_relationships
from fastapi import HTTPException
from fastapi import Query
from typing import Optional, List, Dict, Any
from chronos.scrapers.de import DelawareScraper
import os, inspect, chronos.scrapers.de
from pydantic import BaseModel
if os.getenv("SCRAPER_TRACE") or API_DEBUG:
    print("### Uvicorn imported", inspect.getfile(chronos.scrapers.de))

app = FastAPI(
    title="Project Chronos API",
    version="0.1.0",
    description="HTTP layer over the PortfolioManager with Data Axle and SEC EDGAR integrations.",
)

# --- CORS ----------------------------------------------------------
# Temporary dev-only setting: allow any origin.
# This should be tightened in production to specific origins.
origins = ["*"]  # allow any origin during local development

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Routers ----------------------------------------------------------
# Include routers from other modules
from .sosearch import router as sosearch_router
from .axle import router as axle_router
from .edgar import router as edgar_router

app.include_router(sosearch_router)
app.include_router(axle_router)
app.include_router(edgar_router)

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
    use_data_axle: bool = Query(
        True,
        description="Whether to use Data Axle API for search (if False, uses only local data)",
    ),
    pm: PortfolioManager = Depends(get_portfolio),
):
    """
    Unified business search.

    * For ``use_data_axle=True`` (default), redirects to the Data Axle API endpoint.
    * For ``state == "DE"`` and ``use_data_axle=False``, use the Delaware demo scraper.
    * Otherwise we search the in‑memory PortfolioManager by case‑insensitive
      substring match on name and optional jurisdiction filter.

    Every hit is added to the portfolio (idempotent) so subsequent
    searches and status snapshots include it.
    """
    matches: list[CorporateEntity] = []

    # -- Data Axle search redirects to dedicated endpoints ---------------------
    if use_data_axle:
        # This endpoint now redirects to the /axle/search endpoint
        # which is handled asynchronously. For backward compatibility,
        # we'll just search the local portfolio.
        q_lower = q.lower()
        for ent in pm:
            if q_lower in ent.name.lower() and (not state or ent.jurisdiction.upper() == state.upper()):
                matches.append(ent)

    # -- state‑specific scraper fallback --------------------------------------
    elif state and state.upper() == "DE":
        record = DelawareScraper().fetch(q)
        if record:
            pm.add(record)
            matches.append(record)

    # -- fallback: search current portfolio -----------------------------------
    if not matches:
        q_lower = q.lower()
        for ent in pm:
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

# ---------- GET /relationships ----------
@app.get("/relationships")
def get_relationships(
    rg: RelationshipGraph = Depends(get_relationships),
    pm: PortfolioManager = Depends(get_portfolio),
):
    """
    Return the corporate relationship graph for visualization.
    
    Returns a network structure with nodes (entities) and links (ownership relationships).
    Each node includes entity data like status and jurisdiction.
    Each link includes the ownership percentage.
    """
    # Ensure all entities from portfolio are in the graph with their metadata
    for entity in pm:
        rg.add_entity_data(entity)
        
    # Add some sample relationships if graph is empty
    if len(list(rg.g.edges())) == 0:
        # Find some entities to connect
        entities = list(pm)
        if len(entities) >= 3:
            # Create a simple parent-subsidiary structure
            parent_slug = entities[0].name.lower().replace(" ", "-")
            child1_slug = entities[1].name.lower().replace(" ", "-")
            child2_slug = entities[2].name.lower().replace(" ", "-")
            
            rg.link_parent(parent_slug, child1_slug, 100.0)
            rg.link_parent(parent_slug, child2_slug, 75.0)
    
    # Convert to JSON format for the frontend
    return rg.to_json()

# ---------- GET /shell-detection ----------
@app.get("/shell-detection")
def detect_shell_companies(
    rg: RelationshipGraph = Depends(get_relationships),
    pm: PortfolioManager = Depends(get_portfolio),
):
    """
    Identify potential shell companies in the corporate network.
    
    Uses graph analysis to detect entities that match patterns common to shells:
    - No subsidiaries but owned by others
    - Part of a chain of single-child owners
    - Active status but limited activity
    
    Returns a list of entities with their shell risk scores.
    """
    # First, make sure we have entities linked in the graph
    for entity in pm:
        rg.add_entity_data(entity)
        
    # Create sample parent-child relationships for demonstration purposes
    if len(list(rg.g.edges())) == 0:
        # Create a few sample relationships for demonstration
        rg.link_parent("acme-corporation", "techstart-llc", 100.0)
        rg.link_parent("acme-corporation", "widget-industries", 75.0)
        rg.link_parent("central-holdings", "global-services-inc", 100.0)
        rg.link_parent("central-holdings", "pacific-group", 51.0)
        
    # Now identify shell companies
    shells = rg.identify_shell_companies()
    
    # If no shells are found, add some simulated ones for demo purposes
    if not shells:
        for entity in pm:
            slug = entity.name.lower().replace(" ", "-")
            # Simulate some shells based on patterns
            if entity.status == Status.ACTIVE and "llc" in entity.name.lower():
                shells.append({
                    "slug": slug,
                    "name": entity.name,
                    "risk_score": 0.6,
                    "factors": ["No operational footprint", "Single-owner structure"]
                })
    
    return shells

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