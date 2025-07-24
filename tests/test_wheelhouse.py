"""
Tests for the Wheelhouse API client.

This module tests the WheelhouseClient including retry logic,
error handling, and data fetching capabilities.
"""

import json
import pytest
import requests
from unittest.mock import Mock, patch, MagicMock

from src.srg_rm_copilot.config import Config
from src.srg_rm_copilot.wheelhouse import (
    WheelhouseClient,
    WheelhouseAPIError,
    WheelhouseRateLimitError,
)


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config(
        wheelhouse_api_key="test_api_key",
        wheelhouse_user_api_key="test_user_api_key",
        wheelhouse_base_url="https://api.usewheelhouse.com/wheelhouse_pro_api",
        etl_batch_size=50,
        etl_max_retries=2,
        etl_timeout=10.0,
    )


@pytest.fixture
def client(config):
    """Create a test Wheelhouse client."""
    return WheelhouseClient(config)


@pytest.fixture
def mock_requests(monkeypatch):
    """Create a monkeypatched requests mock fixture."""
    class MockRequestsHelper:
        def __init__(self):
            self.responses = []
            self.call_count = 0
            self.exception = None
            
        def add_response(self, json_data=None, status_code=200, headers=None, exc=None):
            """Add a response to the mock queue."""
            if exc:
                self.exception = exc
                return
                
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_response.json.return_value = json_data or {}
            mock_response.headers = headers or {}
            mock_response.text = ""
            self.responses.append(mock_response)
    
    helper = MockRequestsHelper()
    
    def mock_request(*args, **kwargs):
        if helper.exception:
            raise helper.exception
        if helper.call_count < len(helper.responses):
            resp = helper.responses[helper.call_count]
            helper.call_count += 1
            return resp
        # If we run out of responses, return the last one or a default
        if helper.responses:
            return helper.responses[-1]
        # Default response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.headers = {}
        mock_response.text = ""
        return mock_response
    
    # Mock the session request method directly
    monkeypatch.setattr('requests.Session.request', mock_request)
    
    return helper


@pytest.fixture
def sample_listing_data():
    """Sample listing data for testing."""
    return {
        "listings": [
            {
                "id": "listing_1",
                "name": "Beautiful Apartment",
                "price_per_night": 150.0,
                "address": "123 Main St",
                "room_type": "Entire home/apt",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-02T00:00:00Z",
            },
            {
                "id": "listing_2", 
                "name": "Cozy Studio",
                "price_per_night": 85.0,
                "address": "456 Oak Ave",
                "room_type": "Private room",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-02T00:00:00Z",
            }
        ],
        "total": 2,
        "offset": 0,
        "limit": 50,
    }


class TestWheelhouseClient:
    """Test cases for WheelhouseClient."""
    
    def test_client_initialization(self, config):
        """Test client initializes properly with valid config."""
        client = WheelhouseClient(config)
        assert client.config == config
        assert client.base_url == "https://api.usewheelhouse.com/wheelhouse_pro_api"
        assert client.session is not None
    
    def test_client_initialization_missing_keys(self):
        """Test client raises error with missing API keys."""
        config = Config(
            wheelhouse_api_key=None,
            wheelhouse_user_api_key="test_user_key"
        )
        
        with pytest.raises(ValueError, match="WHEELHOUSE_API_KEY"):
            WheelhouseClient(config)
    
    def test_get_listings_success(self, client, sample_listing_data, mock_requests):
        """Test successful listings retrieval."""
        # Mock successful API response
        mock_requests.add_response(
            json_data=sample_listing_data,
            status_code=200
        )
        
        result = client.get_listings("2025-01-01", limit=50)
        
        assert result == sample_listing_data
        assert len(result["listings"]) == 2
        assert result["total"] == 2
    
    def test_get_listings_with_filters(self, client, sample_listing_data, mock_requests):
        """Test listings retrieval with filters."""
        mock_requests.add_response(
            json_data=sample_listing_data,
            status_code=200
        )
        
        filters = {"property_type": "apartment", "min_price": 100}
        result = client.get_listings("2025-01-01", filters=filters)
        
        assert result == sample_listing_data
    
    def test_rate_limit_handling(self, client, mock_requests):
        """Test handling of 429 rate limit responses."""
        # First request returns rate limit
        mock_requests.add_response(
            json_data={"error": "Rate limit exceeded"},
            status_code=429,
            headers={"Retry-After": "2"}
        )
        # Second succeeds
        mock_requests.add_response(
            json_data={"listings": [], "total": 0},
            status_code=200
        )
        
        # The retry mechanism should handle the rate limit
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = client.get_listings("2025-01-01")
            
        assert result["total"] == 0
    
    def test_api_error_handling(self, client, mock_requests):
        """Test handling of API errors."""
        mock_requests.add_response(
            json_data={"error": "Invalid date format"},
            status_code=400
        )
        
        with pytest.raises(WheelhouseAPIError, match="Invalid date format"):
            client.get_listings("invalid-date")
    
    def test_get_all_listings_pagination(self, client, mock_requests):
        """Test pagination in get_all_listings_for_date."""
        # First page
        page1_data = {
            "listings": [{"id": f"listing_{i}"} for i in range(50)],
            "total": 75,
            "offset": 0,
            "limit": 50
        }
        
        # Second page  
        page2_data = {
            "listings": [{"id": f"listing_{i}"} for i in range(50, 75)],
            "total": 75,
            "offset": 50,
            "limit": 50
        }
        
        mock_requests.add_response(json_data=page1_data, status_code=200)
        mock_requests.add_response(json_data=page2_data, status_code=200)
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            all_listings = client.get_all_listings_for_date("2025-01-01", batch_size=50)
        
        assert len(all_listings) == 75
        assert all_listings[0]["id"] == "listing_0"
        assert all_listings[-1]["id"] == "listing_74"
    
    def test_get_listing_details(self, client, mock_requests):
        """Test getting detailed listing information."""
        listing_detail = {
            "id": "listing_123",
            "name": "Luxury Condo",
            "description": "A beautiful luxury condo...",
            "amenities": ["wifi", "kitchen", "parking"],
            "reviews": []
        }
        
        mock_requests.add_response(
            json_data=listing_detail,
            status_code=200
        )
        
        result = client.get_listing_details("listing_123")
        
        assert result == listing_detail
        assert result["id"] == "listing_123"
        assert "amenities" in result
    
    def test_health_check_success(self, client, mock_requests):
        """Test successful health check."""
        mock_requests.add_response(
            json_data={"status": "ok"},
            status_code=200
        )
        
        result = client.health_check()
        assert result is True
    
    def test_health_check_failure(self, client, mock_requests):
        """Test health check failure."""
        mock_requests.add_response(
            status_code=500
        )
        
        result = client.health_check()
        assert result is False
    
    def test_session_configuration(self, client):
        """Test that session is configured correctly."""
        session = client.session
        
        # Check headers
        assert "Authorization" in session.headers
        assert "X-User-API-Key" in session.headers
        assert session.headers["Authorization"] == "Bearer test_api_key"
        assert session.headers["X-User-API-Key"] == "test_user_api_key"
        
        # Note: timeout is set per-request, not on session
    
    def test_retry_exhaustion(self, client, mock_requests):
        """Test behavior when all retries are exhausted."""
        # All requests return rate limit (more than max retries)
        for _ in range(6):  # More than max retries
            mock_requests.add_response(
                status_code=429,
                headers={"Retry-After": "1"}
            )
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(WheelhouseRateLimitError):
                client.get_listings("2025-01-01")
    
    def test_empty_response_handling(self, client, mock_requests):
        """Test handling of empty responses."""
        mock_requests.add_response(
            json_data={"listings": [], "total": 0},
            status_code=200
        )
        
        all_listings = client.get_all_listings_for_date("2025-01-01")
        assert all_listings == []
    
    def test_network_error_handling(self, client, mock_requests):
        """Test handling of network errors."""
        mock_requests.add_response(
            exc=requests.exceptions.ConnectionError("Connection failed")
        )
        
        with pytest.raises(WheelhouseAPIError, match="Request failed"):
            client.get_listings("2025-01-01")
