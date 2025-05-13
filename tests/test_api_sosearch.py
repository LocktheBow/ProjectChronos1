"""
Tests for the /sosearch API endpoints.

These tests use FastAPI TestClient to test the API endpoints directly,
with mocked OpenCorporates and EDGAR responses.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from chronos.models import CorporateEntity, Status
from chronos.scrapers.openc import OpenCorporatesScraper
from chronos.scrapers.edgar import EdgarClient


# Create test client
client = TestClient(app)

# Test data fixtures - same as in test_scraper_openc.py
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

# Mock OpenCorporatesScraper to return predetermined results
@pytest.fixture
def mock_openc_scraper():
    with patch('api.sosearch.OpenCorporatesScraper') as mock:
        # Create mock instance to return from constructor
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Configure the search method
        def mock_search(query, jurisdiction=None):
            # Return two test entities
            return [
                CorporateEntity(
                    name="ACME CORPORATION",
                    jurisdiction="DE",
                    formed="2020-01-01",
                    status=Status.ACTIVE
                ),
                CorporateEntity(
                    name="ACME SUBSIDIARIES INC",
                    jurisdiction="DE",
                    formed="2021-02-02",
                    status=Status.DISSOLVED
                )
            ]
            
        # Configure the fetch_by_id method
        def mock_fetch_by_id(company_number, jurisdiction):
            return CorporateEntity(
                name="ACME CORPORATION",
                jurisdiction=jurisdiction,
                formed="2020-01-01",
                status=Status.ACTIVE
            )
            
        mock_instance.search.side_effect = mock_search
        mock_instance.fetch_by_id.side_effect = mock_fetch_by_id
        
        yield mock_instance


# Mock EdgarClient for testing the EDGAR integration
@pytest.fixture
def mock_edgar_client():
    with patch('api.sosearch.EdgarClient') as mock:
        # Create mock instance to return from constructor
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Configure the enrich_entity method to add CIK to notes
        def mock_enrich(entity):
            entity.notes = "SEC CIK: 0000789019"
            return entity
            
        mock_instance.enrich_entity.side_effect = mock_enrich
        
        yield mock_instance


# Mock the ENABLE_EDGAR environment variable
@pytest.fixture
def mock_enable_edgar():
    with patch('api.sosearch.ENABLE_EDGAR', True):
        yield


class TestSosearchAPI:
    """Test suite for the /sosearch API endpoints"""
    
    def test_sosearch_endpoint(self, mock_openc_scraper):
        """Test the /sosearch endpoint with mocked scraper"""
        response = client.get("/sosearch?q=ACME")
        
        # Verify API response
        assert response.status_code == 200
        
        # Should have received 2 entities
        data = response.json()
        assert len(data) == 2
        
        # Check first entity
        assert data[0]["name"] == "ACME CORPORATION"
        assert data[0]["jurisdiction"] == "DE"
        assert data[0]["status"] == "ACTIVE"
        
    def test_sosearch_with_jurisdiction(self, mock_openc_scraper):
        """Test the /sosearch endpoint with jurisdiction filter"""
        response = client.get("/sosearch?q=ACME&jurisdiction=DE")
        
        # Verify API response
        assert response.status_code == 200
        
        # Verify the jurisdiction was passed to the scraper
        mock_openc_scraper.search.assert_called_once()
        args, kwargs = mock_openc_scraper.search.call_args
        assert kwargs["jurisdiction"] == "DE"
        
    def test_sosearch_by_id(self, mock_openc_scraper):
        """Test the /sosearch/{jurisdiction}/{company_number} endpoint"""
        response = client.get("/sosearch/DE/12345678")
        
        # Verify API response
        assert response.status_code == 200
        
        # Check entity data
        data = response.json()
        assert data["name"] == "ACME CORPORATION"
        assert data["jurisdiction"] == "DE"
        
        # Verify the scraper was called with correct parameters
        mock_openc_scraper.fetch_by_id.assert_called_once_with("12345678", "DE")
        
    def test_sosearch_with_edgar_enrichment(self, mock_openc_scraper, mock_edgar_client, mock_enable_edgar):
        """Test the /sosearch endpoint with EDGAR enrichment enabled"""
        response = client.get("/sosearch?q=ACME")
        
        # Verify API response
        assert response.status_code == 200
        
        # Should have called the edgar client to enrich entities
        mock_edgar_client.enrich_entity.assert_called()
        
    def test_sosearch_not_found(self, mock_openc_scraper):
        """Test the /sosearch endpoint when no entities are found"""
        # Configure the mock to return empty results
        mock_openc_scraper.search.return_value = []
        
        response = client.get("/sosearch?q=NONEXISTENT")
        
        # Should return 404 Not Found
        assert response.status_code == 404
        
        # Error message should indicate no entities found
        data = response.json()
        assert "detail" in data
        assert "No matching entities found" in data["detail"]
        
    def test_search_endpoint_with_opencorporates(self, mock_openc_scraper):
        """Test the /search endpoint with OpenCorporates enabled"""
        response = client.get("/search?q=ACME&use_opencorporates=true")
        
        # Verify API response
        assert response.status_code == 200
        
        # Should have called the OpenCorporates scraper
        mock_openc_scraper.search.assert_called_once()
"""