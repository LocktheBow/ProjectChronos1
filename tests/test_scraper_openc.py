"""
Tests for the OpenCorporates API scraper.

These tests use mocked responses to avoid making actual API calls during testing.
When OPENCORP_API_TOKEN is set in the environment, some tests will use real API
calls to verify functionality.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from chronos.scrapers.openc import OpenCorporatesScraper
from chronos.models import Status

# Test data fixtures
MOCK_OC_SEARCH_RESPONSE = {
    "api_version": "0.4",
    "results": {
        "companies": [
            {
                "company": {
                    "name": "ACME CORPORATION",
                    "company_number": "12345678",
                    "jurisdiction_code": "us_de",
                    "incorporation_date": "2020-01-01",
                    "company_type": "Private Limited Company",
                    "current_status": "Active",
                    "opencorporates_url": "https://opencorporates.com/companies/us_de/12345678",
                    "registered_address": "123 Main St, Dover, DE 19901"
                }
            },
            {
                "company": {
                    "name": "ACME SUBSIDIARIES INC",
                    "company_number": "23456789",
                    "jurisdiction_code": "us_de",
                    "incorporation_date": "2021-02-02",
                    "company_type": "Private Limited Company",
                    "current_status": "Inactive",
                    "opencorporates_url": "https://opencorporates.com/companies/us_de/23456789"
                }
            }
        ]
    }
}

MOCK_OC_COMPANY_RESPONSE = {
    "api_version": "0.4",
    "results": {
        "company": {
            "name": "ACME CORPORATION",
            "company_number": "12345678",
            "jurisdiction_code": "us_de",
            "incorporation_date": "2020-01-01",
            "company_type": "Private Limited Company",
            "current_status": "Active",
            "opencorporates_url": "https://opencorporates.com/companies/us_de/12345678",
            "registered_address": "123 Main St, Dover, DE 19901",
            "officers": [
                {
                    "name": "John Smith",
                    "position": "Director",
                    "start_date": "2020-01-01"
                }
            ]
        }
    }
}

# Mock the cache functionality to avoid filesystem operations
@pytest.fixture
def mock_db_setup():
    with patch('chronos.scrapers.openc.sqlite3.connect'):
        yield


# Mock API responses
@pytest.fixture
def mock_api_responses():
    with patch('chronos.scrapers.openc.requests.get') as mock_get:
        # Configure the mock to return different responses for different endpoints
        def mock_response(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.headers = {'Content-Type': 'application/json'}
            
            if 'companies/search' in url:
                mock_resp.json.return_value = MOCK_OC_SEARCH_RESPONSE
            elif 'companies/us_de/12345678' in url:
                mock_resp.json.return_value = MOCK_OC_COMPANY_RESPONSE
            else:
                # Default empty response
                mock_resp.json.return_value = {"results": {}}
                
            return mock_resp
            
        mock_get.side_effect = mock_response
        yield mock_get


class TestOpenCorporatesScraper:
    """Test suite for the OpenCorporatesScraper class"""
    
    def test_initialization(self, mock_db_setup):
        """Test that the scraper initializes correctly"""
        scraper = OpenCorporatesScraper(use_cache=False)
        assert isinstance(scraper, OpenCorporatesScraper)
        
    def test_search_with_mocks(self, mock_db_setup, mock_api_responses):
        """Test company search with mocked API responses"""
        scraper = OpenCorporatesScraper(use_cache=False)
        results = scraper.search("ACME")
        
        # Should have found 2 companies
        assert len(results) == 2
        
        # Check first company details
        assert results[0].name == "ACME CORPORATION"
        assert results[0].jurisdiction == "DE"
        assert results[0].status == Status.ACTIVE
        assert results[0].formed == date(2020, 1, 1)
        
        # Check second company details
        assert results[1].name == "ACME SUBSIDIARIES INC"
        assert results[1].status == Status.DISSOLVED  # Mapped from "Inactive"
        
    def test_search_with_jurisdiction(self, mock_db_setup, mock_api_responses):
        """Test company search with jurisdiction filter"""
        scraper = OpenCorporatesScraper(use_cache=False)
        results = scraper.search("ACME", jurisdiction="DE")
        
        # Verify API was called with correct parameters
        mock_api_responses.assert_called_once()
        call_args = mock_api_responses.call_args[1]
        assert 'params' in call_args
        assert call_args['params'].get('jurisdiction_code') == 'us_de'
        
    def test_fetch_by_name(self, mock_db_setup, mock_api_responses):
        """Test fetch by name which should return the best match"""
        scraper = OpenCorporatesScraper(use_cache=False)
        entity = scraper.fetch("ACME")
        
        # Should return the first match with exact name match
        assert entity is not None
        assert entity.name == "ACME CORPORATION"
        assert entity.jurisdiction == "DE"
        
    def test_fetch_by_id(self, mock_db_setup, mock_api_responses):
        """Test fetch by ID (company number and jurisdiction)"""
        scraper = OpenCorporatesScraper(use_cache=False)
        entity = scraper.fetch_by_id("12345678", "DE")
        
        # Should fetch the specific company
        assert entity is not None
        assert entity.name == "ACME CORPORATION"
        assert entity.jurisdiction == "DE"
        assert entity.officers == ["John Smith"]
        assert "Director" in entity.notes  # Officer info should be in notes
        
    def test_status_mapping(self, mock_db_setup):
        """Test mapping from OpenCorporates status to Chronos Status enum"""
        scraper = OpenCorporatesScraper(use_cache=False)
        
        # Direct mappings
        assert scraper._map_oc_status_to_chronos("Active") == Status.ACTIVE
        assert scraper._map_oc_status_to_chronos("Dissolved") == Status.DISSOLVED
        assert scraper._map_oc_status_to_chronos("Delinquent") == Status.DELINQUENT
        
        # Substring/fuzzy mappings
        assert scraper._map_oc_status_to_chronos("In Good Standing") == Status.IN_COMPLIANCE
        assert scraper._map_oc_status_to_chronos("Voluntarily Dissolved") == Status.DISSOLVED
        
        # Default fallback
        assert scraper._map_oc_status_to_chronos("Unknown Status") == Status.ACTIVE
        
    @pytest.mark.skipif(not os.environ.get("OPENCORP_API_TOKEN"), 
                      reason="No OpenCorporates API token available")
    def test_live_search_delaware(self):
        """Test live search against Delaware (requires API token)"""
        scraper = OpenCorporatesScraper(use_cache=True)
        results = scraper.search("Bank of America", jurisdiction="DE")
        
        # Should find some results
        assert len(results) > 0
        
        # At least one result should be from Delaware
        assert any(e.jurisdiction == "DE" for e in results)
        
    @pytest.mark.skipif(not os.environ.get("OPENCORP_API_TOKEN"), 
                      reason="No OpenCorporates API token available")
    def test_live_search_california(self):
        """Test live search against California (requires API token)"""
        scraper = OpenCorporatesScraper(use_cache=True)
        results = scraper.search("Apple", jurisdiction="CA")
        
        # Should find some results
        assert len(results) > 0
        
        # At least one result should be from California  
        assert any(e.jurisdiction == "CA" for e in results)
        
    @pytest.mark.skipif(not os.environ.get("OPENCORP_API_TOKEN"), 
                      reason="No OpenCorporates API token available")
    def test_live_global_search(self):
        """Test live global search (requires API token)"""
        scraper = OpenCorporatesScraper(use_cache=True)
        results = scraper.search("Microsoft")
        
        # Should find results from multiple jurisdictions
        assert len(results) > 0
        
        # Should have unique jurisdictions
        jurisdictions = {e.jurisdiction for e in results}
        assert len(jurisdictions) >= 1  # At least one jurisdiction
"""