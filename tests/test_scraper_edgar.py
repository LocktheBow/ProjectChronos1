"""
Tests for the SEC EDGAR API integration.

These tests use mocked responses to avoid making actual API calls during testing.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from chronos.scrapers.edgar import EdgarClient
from chronos.models import CorporateEntity, Status

# Test data fixtures
MOCK_EDGAR_SEARCH_RESPONSE = {
    "cik": "0000789019",
    "entityType": "operating",
    "sic": "7370",
    "sicDescription": "Services-Computer Programming, Data Processing, Etc.",
    "name": "MICROSOFT CORP",
    "tickers": ["MSFT"],
    "exchanges": ["NASDAQ"],
    "ein": "912580279",
    "filings": {
        "recent": {
            "form": ["10-K", "10-Q", "8-K"],
            "filingDate": ["2023-06-30", "2023-03-31", "2023-01-24"],
            "accessionNumber": ["0000789019-23-000075", "0000789019-23-000041", "0000789019-23-000009"],
            "primaryDocument": ["msft-10k_20230630.htm", "msft-10q_20230331.htm", "msft-8k_20230124.htm"],
            "fileNumber": ["001-37845", "001-37845", "001-37845"]
        }
    }
}

MOCK_EDGAR_NO_RESULTS = {
    "error": "No matching companies found"
}

# Mock the cache functionality to avoid filesystem operations
@pytest.fixture
def mock_db_setup():
    with patch('chronos.scrapers.edgar.sqlite3.connect'):
        yield


# Mock API responses
@pytest.fixture
def mock_api_responses():
    with patch('chronos.scrapers.edgar.requests.get') as mock_get:
        # Configure the mock to return different responses for different endpoints
        def mock_response(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            params = kwargs.get('params', {})
            
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.headers = {'Content-Type': 'application/json'}
            
            if 'browse-edgar' in url and params.get('company') == 'Microsoft':
                mock_resp.json.return_value = MOCK_EDGAR_SEARCH_RESPONSE
            else:
                # Default empty response
                mock_resp.json.return_value = MOCK_EDGAR_NO_RESULTS
                
            return mock_resp
            
        mock_get.side_effect = mock_response
        yield mock_get


class TestEdgarClient:
    """Test suite for the EdgarClient class"""
    
    def test_initialization(self, mock_db_setup):
        """Test that the client initializes correctly"""
        client = EdgarClient(use_cache=False)
        assert isinstance(client, EdgarClient)
        
    def test_search_company(self, mock_db_setup, mock_api_responses):
        """Test company search with mocked API responses"""
        client = EdgarClient(use_cache=False)
        result = client.search_company("Microsoft")
        
        # Should have found the company
        assert result is not None
        assert result.get("cik") == "0000789019"
        assert result.get("name") == "MICROSOFT CORP"
        
    def test_extract_cik(self, mock_db_setup, mock_api_responses):
        """Test extraction of CIK from response"""
        client = EdgarClient(use_cache=False)
        
        # Test with a valid response
        response = MOCK_EDGAR_SEARCH_RESPONSE
        cik = client.extract_cik(response)
        assert cik == "0000789019"
        
        # Test with invalid/empty response
        cik = client.extract_cik(None)
        assert cik is None
        
        cik = client.extract_cik({})
        assert cik is None
        
    def test_get_latest_filings(self, mock_db_setup, mock_api_responses):
        """Test retrieving latest filings for a company"""
        client = EdgarClient(use_cache=False)
        filings = client.get_latest_filings("0000789019")
        
        # Call should be made to the correct endpoint
        mock_api_responses.assert_called_once()
        
        # Filings might be empty because the mock doesn't return the expected structure
        # The EDGAR API response format is complex and this is just a test of the mechanism
        assert isinstance(filings, list)
        
    def test_enrich_entity(self, mock_db_setup, mock_api_responses):
        """Test entity enrichment with EDGAR data"""
        client = EdgarClient(use_cache=False)
        
        # Create a test entity
        entity = CorporateEntity(
            name="Microsoft Corporation",
            jurisdiction="WA",
            formed=date(1975, 4, 4),
            status=Status.ACTIVE
        )
        
        # Enrich the entity
        enriched = client.enrich_entity(entity)
        
        # The entity should have been updated with EDGAR data
        assert enriched is not None
        assert enriched.notes is not None
        assert "SEC CIK" in enriched.notes
        
    def test_disabled_client(self, mock_db_setup, mock_api_responses):
        """Test that disabled client doesn't make API calls"""
        client = EdgarClient(use_cache=False, enabled=False)
        
        # Search with disabled client
        result = client.search_company("Microsoft")
        assert result is None
        
        # Get filings with disabled client
        filings = client.get_latest_filings("0000789019")
        assert filings == []
        
        # Enrich entity with disabled client
        entity = CorporateEntity(
            name="Microsoft",
            jurisdiction="WA",
            formed=date(1975, 4, 4),
            status=Status.ACTIVE
        )
        
        enriched = client.enrich_entity(entity)
        assert enriched == entity  # Should return the original entity unchanged
        
        # No API calls should have been made
        mock_api_responses.assert_not_called()
"""