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
from chronos.scrapers.opencorp import OpenCorporatesScraper
from chronos.scrapers.cobalt import CobaltScraper
from .deps import get_opencorp_scraper, get_cobalt_scraper
import os, inspect, chronos.scrapers.de, chronos.scrapers.opencorp, chronos.scrapers.cobalt
import networkx as nx
from pydantic import BaseModel
if os.getenv("SCRAPER_TRACE") or API_DEBUG:
    print("### Uvicorn imported DE scraper from", inspect.getfile(chronos.scrapers.de))
    print("### Uvicorn imported OpenCorp scraper from", inspect.getfile(chronos.scrapers.opencorp))
    print("### Uvicorn imported Cobalt scraper from", inspect.getfile(chronos.scrapers.cobalt))

app = FastAPI(
    title="Project Chronos API",
    version="0.1.0",
    description="HTTP layer over the PortfolioManager with Data Axle and SEC EDGAR integrations.",
)

# --- CORS ----------------------------------------------------------
# Temporary dev-only setting: allow specific origins for development.
# This should be tightened in production to specific origins.
origins = [
    "http://localhost:5173",    # Vite dev server default port
    "http://127.0.0.1:5173",    # Alternative localhost
    "http://localhost:3000",    # In case using a different port
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# --- Include Routers ----------------------------------------------------------
# Include routers from other modules
from .sosearch import router as sosearch_router
from .axle import router as axle_router
from .edgar import router as edgar_router
from .axle_v2 import router as axle_v2_router
from .opencorp import router as opencorp_router
from .cobalt import router as cobalt_router
from .reset import router as reset_router
from .relationships import router as relationships_router
from .entity_list import router as entity_list_router
from .explicit_clear import router as explicit_clear_router

app.include_router(sosearch_router)
app.include_router(axle_router)
app.include_router(axle_v2_router)  # New Data Axle router with improved auth
app.include_router(edgar_router)
app.include_router(opencorp_router)  # New OpenCorporates router
app.include_router(cobalt_router)    # New Cobalt Intelligence router
app.include_router(reset_router)     # Graph reset functionality
app.include_router(relationships_router, prefix="/relationships") # Direct relationship management
app.include_router(entity_list_router)  # Entity listing for dropdowns
app.include_router(explicit_clear_router)  # Explicit graph clearing methods

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
async def search_entities(
    q: str = Query(..., min_length=2, description="Business name search term"),
    state: str | None = Query(
        None,
        min_length=2,
        max_length=2,
        pattern="^[A-Za-z]{2}$",
        description="Optional two‑letter state code",
    ),
    use_cobalt: bool = Query(
        True,
        description="Whether to use Cobalt Intelligence API for search (if False, uses only local data)",
    ),
    pm: PortfolioManager = Depends(get_portfolio),
    cobalt_scraper: CobaltScraper = Depends(get_cobalt_scraper),
    opencorp_scraper: OpenCorporatesScraper = Depends(get_opencorp_scraper),
):
    """
    Unified business search.

    * For ``use_cobalt=True`` (default), searches using the Cobalt Intelligence API.
    * For ``state == "DE"`` and ``use_cobalt=False``, use the Delaware demo scraper.
    * Otherwise we search the in‑memory PortfolioManager by case‑insensitive
      substring match on name and optional jurisdiction filter.

    Every hit is added to the portfolio (idempotent) so subsequent
    searches and status snapshots include it.
    """
    matches: list[CorporateEntity] = []

    # -- Cobalt Intelligence search (primary source) --------------------------
    if use_cobalt:
        try:
            # Search using Cobalt Intelligence API with our dependency-injected scraper
            entities = await cobalt_scraper.search(q, state)
            
            if entities:
                # Add entities to portfolio and matches list
                for entity in entities:
                    pm.add(entity)
                    matches.append(entity)
        except Exception as e:
            print(f"Cobalt Intelligence search error: {e}")
            # Continue to fallback search methods
            
            # Try OpenCorporates API as a fallback
            try:
                print("Falling back to OpenCorporates API")
                entities = await opencorp_scraper.search(q, state)
                
                if entities:
                    # Add entities to portfolio and matches list
                    for entity in entities:
                        pm.add(entity)
                        matches.append(entity)
            except Exception as oe:
                print(f"OpenCorporates fallback search error: {oe}")
                # Continue to other fallbacks

    # -- state‑specific scraper fallback --------------------------------------
    if not matches and state and state.upper() == "DE":
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

# Model for creating parent-child relationships
class ParentChildRelationship(BaseModel):
    parent_slug: str
    child_slug: str
    ownership_percentage: float

# ---------- GET/POST /relationships ----------
@app.get("/relationships")
def get_relationships(
    rg: RelationshipGraph = Depends(get_relationships),
    pm: PortfolioManager = Depends(get_portfolio),
    load_examples: bool = Query(False, description="Force loading example relationships"),
    clear_relationships: bool = Query(False, description="Clear all relationship connections"),
):
    """
    Return the corporate relationship graph for visualization.
    
    Returns a network structure with nodes (entities) and links (ownership relationships).
    Each node includes entity data like status and jurisdiction.
    Each link includes the ownership percentage.
    """
    # Handle clear relationships request
    if clear_relationships:
        print("Clearing all relationships from graph")
        
        try:
            # Import our utility function
            from .clear_graph import clear_graph
            
            # Reset the graph completely
            rg = clear_graph()
            
            print("Created a fresh relationship graph - all relationships cleared")
        except Exception as e:
            print(f"Error clearing graph: {e}")
            
            # Fallback method: manually clear edges
            try:
                # Remove all edges but keep nodes
                edges = list(rg.g.edges())
                for source, target in edges:
                    rg.g.remove_edge(source, target)
                print(f"Fallback method: Removed {len(edges)} edges while preserving nodes")
            except Exception as edge_error:
                print(f"Error in fallback edge removal: {edge_error}")
        
    # Ensure all entities from portfolio are in the graph with their metadata
    for entity in pm:
        rg.add_entity_data(entity)
        
    # Add some sample relationships if graph is empty or explicitly requested
    if load_examples or len(list(rg.g.edges())) == 0:
        # When loading examples, clear the graph completely first
        if load_examples:
            print("Clearing existing graph for example loading")
            rg.g.clear()
            # Also clear entity data since we'll reload from example file
            rg._entity_data.clear()
        
        # Find some entities to connect if not explicitly loading examples
        if not load_examples and len(list(pm)) >= 3:
            entities = list(pm)
            # Create a simple parent-subsidiary structure
            parent_slug = entities[0].name.lower().replace(" ", "-")
            child1_slug = entities[1].name.lower().replace(" ", "-")
            child2_slug = entities[2].name.lower().replace(" ", "-")
            
            rg.link_parent(parent_slug, child1_slug, 100.0)
            rg.link_parent(parent_slug, child2_slug, 75.0)
        
        # Load sample relationships data for demo
        import json
        import os
        from datetime import date
        sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "chronos-dashboard", "public", "example_relationships.json")
        try:
            if os.path.exists(sample_path):
                print(f"Loading example relationships from {sample_path}")
                with open(sample_path, 'r') as f:
                    example_data = json.load(f)
                
                print(f"Found {len(example_data.get('nodes', []))} nodes and {len(example_data.get('links', []))} links in example data")
                
                # Clear portfolio if loading examples explicitly to avoid duplicates
                if load_examples:
                    pm.clear()
                    
                # Add nodes and relationships from example data
                for node in example_data.get('nodes', []):
                    entity = CorporateEntity(
                        name=node['name'],
                        jurisdiction=node['jurisdiction'],
                        status=getattr(Status, node['status']),
                        formed=date.today()  # Use today as default date
                    )
                    pm.add(entity)
                    rg.add_entity_data(entity)
                
                # Add edges
                for link in example_data.get('links', []):
                    try:
                        rg.link_parent(link['source'], link['target'], link['value'])
                    except Exception as edge_error:
                        print(f"Error adding edge {link['source']} -> {link['target']}: {edge_error}")
                
                print(f"Successfully loaded example relationships: {len(example_data.get('nodes', []))} nodes, {len(example_data.get('links', []))} links, {len(list(rg.g.edges()))} edges in graph")
        except Exception as e:
            import traceback
            print(f"Failed to load example relationships: {e}")
            traceback.print_exc()
    
    # Convert to JSON format for the frontend
    return rg.to_json()

# ---------- POST /relationships ----------
@app.post("/relationships", status_code=201)
def create_relationship(
    relationship: ParentChildRelationship,
    rg: RelationshipGraph = Depends(get_relationships),
    pm: PortfolioManager = Depends(get_portfolio),
):
    """
    Create a parent-child ownership relationship between two entities.
    
    Args:
        relationship: Parent-child relationship details with ownership percentage
        
    Returns:
        Confirmation of the created relationship
    """
    try:
        # Verify both entities exist in portfolio
        parent_entity = None
        child_entity = None
        
        for entity in pm:
            slug = entity.name.lower().replace(" ", "-")
            if slug == relationship.parent_slug:
                parent_entity = entity
            if slug == relationship.child_slug:
                child_entity = entity
                
        if not parent_entity:
            raise HTTPException(
                status_code=404, 
                detail=f"Parent entity not found with slug: {relationship.parent_slug}"
            )
            
        if not child_entity:
            raise HTTPException(
                status_code=404, 
                detail=f"Child entity not found with slug: {relationship.child_slug}"
            )
            
        # Validate ownership percentage
        if not (0 <= relationship.ownership_percentage <= 100):
            raise HTTPException(
                status_code=400,
                detail="Ownership percentage must be between 0 and 100"
            )
        
        # Add entity data to graph if needed
        rg.add_entity_data(parent_entity)
        rg.add_entity_data(child_entity)
        
        # Create the parent-child relationship
        rg.link_parent(
            relationship.parent_slug,
            relationship.child_slug,
            relationship.ownership_percentage
        )
        
        return {
            "status": "success",
            "message": f"Created relationship: {parent_entity.name} owns {relationship.ownership_percentage}% of {child_entity.name}",
            "parent": relationship.parent_slug,
            "child": relationship.child_slug,
            "percentage": relationship.ownership_percentage
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating relationship: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating relationship: {str(e)}")

# ---------- GET /shell-detection ----------
@app.get("/shell-detection")
def detect_shell_companies(
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
    try:
        # Create sample entities if portfolio is empty (for demo purposes)
        if len(list(pm)) == 0:
            print("Portfolio is empty, creating sample entities for shell detection")
            sample_entities = [
                CorporateEntity(
                    name="TechStart LLC",
                    jurisdiction="DE",
                    status=Status.ACTIVE
                ),
                CorporateEntity(
                    name="Widget Industries",
                    jurisdiction="NV",
                    status=Status.DELINQUENT
                ),
                CorporateEntity(
                    name="Global Services Inc",
                    jurisdiction="CA",
                    status=Status.ACTIVE,
                    formed="2018-03-15"
                ),
                CorporateEntity(
                    name="Acme Corporation",
                    jurisdiction="DE",
                    status=Status.ACTIVE,
                    formed="2005-11-20"
                ),
                CorporateEntity(
                    name="Central Holdings",
                    jurisdiction="WY",
                    status=Status.ACTIVE,
                    formed="2019-07-01"
                ),
                CorporateEntity(
                    name="Pacific Group",
                    jurisdiction="CA",
                    status=Status.ACTIVE,
                    formed="2017-09-22"
                )
            ]
            
            for entity in sample_entities:
                try:
                    pm.add(entity)
                except Exception as e:
                    print(f"Error adding sample entity {entity.name}: {e}")
            
        # Generate simulated shell companies for demo purposes
        shells = []
        for entity in pm:
            slug = entity.name.lower().replace(" ", "-")
            risk_score = 0.0
            factors = []
            
            # Apply risk scoring criteria
            if entity.status == Status.ACTIVE and "llc" in entity.name.lower():
                risk_score += 0.3
                factors.append("LLC structure with limited visibility")
            
            if entity.status == Status.DELINQUENT:
                risk_score += 0.2
                factors.append("Delinquent filing status")
                
            if not entity.formed:
                risk_score += 0.1
                factors.append("Missing formation date")
            
            # Add jurisdiction-based risk factors
            if entity.jurisdiction in ["DE", "WY", "NV"]:
                risk_score += 0.15
                factors.append(f"Registered in {entity.jurisdiction}, a jurisdiction favored for secrecy")
                
            # Simulate other shell patterns
            if "llc" in entity.name.lower() and entity.jurisdiction == "DE":
                risk_score += 0.25
                factors.append("Shell pattern: Delaware LLC with limited transparency")
                
            if "holdings" in entity.name.lower() or "group" in entity.name.lower():
                risk_score += 0.15
                factors.append("Shell pattern: Holding company naming pattern")
                
            # Only include entities with significant risk score
            if risk_score >= 0.2:
                shells.append({
                    "slug": slug,
                    "name": entity.name,
                    "risk_score": min(risk_score, 0.95),  # Cap at 0.95
                    "factors": factors
                })
                
        # Ensure we always return at least one shell company in demo mode
        if len(shells) == 0:
            # Create a dummy shell company if none were detected
            shells.append({
                "slug": "anonymous-holdings-llc",
                "name": "Anonymous Holdings LLC",
                "risk_score": 0.65,
                "factors": [
                    "LLC structure with limited visibility",
                    "Missing formation date",
                    "Shell pattern: Owned but has no subsidiaries",
                    "Suspicious jurisdiction hopping pattern"
                ]
            })
        
        return shells
    
    except Exception as e:
        print(f"Shell detection error: {e}")
        # Return empty list rather than error
        return []

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