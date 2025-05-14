"""
api.edgar
========

FastAPI router for SEC EDGAR API integration.

This module implements endpoints for searching company information and filings
using the SEC EDGAR API.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from httpx import AsyncClient

from chronos.models import CorporateEntity, Status
from chronos.portfolio import PortfolioManager
from chronos.scrapers.edgar import EdgarClient
from .deps import get_portfolio, get_edgar_client

# Create router
router = APIRouter(prefix="/edgar", tags=["edgar"])


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_companies(
    q: str = Query(..., min_length=2, description="Company name search term"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results to return"),
    edgar_client: AsyncClient = Depends(get_edgar_client),
    pm: PortfolioManager = Depends(get_portfolio),
):
    """
    Search for companies using SEC EDGAR API.
    
    - Accepts a company name query (`q`) and optional result limit
    - Searches SEC EDGAR API and returns normalized results
    - Includes CIK numbers and other company identifiers
    
    Returns a list of matching companies with normalized data structure.
    """
    # Create EDGAR client
    client = EdgarClient(edgar_client)
    
    # Search for companies
    results = await client.search_companies(q, limit=limit)
    
    if not results:
        raise HTTPException(status_code=404, detail="No matching companies found")
    
    # Normalize results
    normalized_results = []
    for result in results:
        company_data = {
            "name": result.get("entity_name", result.get("companyName", "Unknown")),
            "cik": result.get("cik", ""),
            "ticker": result.get("ticker", ""),
            "exchange": result.get("exchange", ""),
            "sic": result.get("sic", ""),
            "sic_description": result.get("sicDescription", result.get("industry_category", "")),
            "filing_date": result.get("filingDate", ""),
            "form": result.get("form", ""),
            "filing_id": result.get("id", ""),
            "incorporation": result.get("state", result.get("stateOrCountry", ""))
        }
        normalized_results.append(company_data)
    
    return normalized_results


@router.get("/filings/{cik}", response_model=List[Dict[str, Any]])
async def get_company_filings(
    cik: str,
    forms: Optional[str] = Query(None, description="Comma-separated list of form types (e.g., '10-K,10-Q')"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results to return"),
    edgar_client: AsyncClient = Depends(get_edgar_client),
):
    """
    Get company filings by CIK.
    
    - Accepts a CIK identifier and optional form types filter
    - Retrieves recent SEC filings for the specified company
    - Can filter by form types (e.g., 10-K, 10-Q, 8-K)
    
    Returns a list of filing information.
    """
    # Create EDGAR client
    client = EdgarClient(edgar_client)
    
    # Parse form types if provided
    form_types = forms.split(",") if forms else None
    
    # Get filings
    filings = await client.get_company_filings(cik, form_types=form_types, limit=limit)
    
    if not filings:
        raise HTTPException(status_code=404, detail=f"No filings found for CIK: {cik}")
    
    # Normalize results
    normalized_filings = []
    for filing in filings:
        filing_data = {
            "form": filing.get("form", "Unknown"),
            "filing_date": filing.get("filingDate", ""),
            "accession_number": filing.get("accessionNumber", ""),
            "file_url": filing.get("fileUrl", ""),
            "description": filing.get("description", ""),
            "primary_document": filing.get("primaryDocument", "")
        }
        normalized_filings.append(filing_data)
    
    return normalized_filings


@router.get("/entity/{cik}", response_model=Dict[str, Any])
async def get_company_by_cik(
    cik: str,
    edgar_client: AsyncClient = Depends(get_edgar_client),
    pm: PortfolioManager = Depends(get_portfolio),
):
    """
    Get company information by CIK and convert to entity format.
    
    - Accepts a CIK identifier
    - Retrieves company information and creates a CorporateEntity
    - Retrieves recent filings and adds to entity notes
    
    Returns a normalized company entity.
    """
    # Create EDGAR client
    client = EdgarClient(edgar_client)
    
    # Search for company by CIK
    companies = await client.search_companies(cik, limit=1)
    
    if not companies:
        raise HTTPException(status_code=404, detail=f"No company found for CIK: {cik}")
    
    company = companies[0]
    
    # Create a CorporateEntity
    entity = CorporateEntity(
        name=company.get("name", "Unknown"),
        jurisdiction=company.get("incorporation", {}).get("stateOrCountry", "US"),
        status=Status.ACTIVE,  # Default status, SEC doesn't provide status info
        officers=[],  # SEC API doesn't provide officers
    )
    
    # Add SEC information to notes
    sec_notes = [f"SEC CIK: {cik}"]
    
    if company.get("ticker"):
        sec_notes.append(f"Ticker: {company['ticker']}")
    
    if company.get("sicDescription"):
        sec_notes.append(f"Industry: {company['sicDescription']}")
    
    # Get filings and add to notes
    filings = await client.get_company_filings(cik, limit=3)
    if filings:
        sec_notes.append("\nRecent SEC Filings:")
        for filing in filings:
            sec_notes.append(f"- {filing.get('form', 'Unknown')} ({filing.get('filingDate', '')})")
    
    entity.notes = "\n".join(sec_notes)
    
    # Add entity to portfolio
    pm.add(entity)
    
    # Return normalized entity
    return {
        "slug": entity.name.lower().replace(" ", "-"),
        "name": entity.name,
        "jurisdiction": entity.jurisdiction,
        "status": entity.status.name,
        "formed": entity.formed.isoformat() if entity.formed else None,
        "officers": entity.officers,
        "notes": entity.notes,
        "sec_data": {
            "cik": cik,
            "ticker": company.get("ticker"),
            "exchange": company.get("exchanges", [None])[0],
            "sic": company.get("sic"),
            "sic_description": company.get("sicDescription")
        }
    }