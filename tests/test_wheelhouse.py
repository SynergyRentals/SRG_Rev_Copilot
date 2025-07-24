"""
Tests for the Wheelhouse API client.

This module tests the WheelhouseClient including retry logic,
error handling, and data fetching capabilities.
"""

import json
import pytest
import httpx
from unittest.mock import Mock, patch

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
        wheelhouse_base_url="https://api.wheelhouse.test",
        etl_batch_size=50,
        etl_max_retries=2,
        etl_timeout=10.0,
    )


@pytest.fixture
def client(config):
    """Create a test Wheelhouse client."""
    return WheelhouseClient(config)


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
        assert client.base_url == "https://api.wheelhouse.test"
        assert client.session is not None
    
    def test_client_initialization_missing_keys(self):
        """Test client raises error with missing API keys."""
        config = Config(
            wheelhouse_api_key=None,
            wheelhouse_user_api_key="test_user_key"
        )
        
        with pytest.raises(ValueError, match="WHEELHOUSE_API_KEY"):
            WheelhouseClient(config)
    
    @pytest.mark.asyncio
    async def test_get_listings_success(self, client, sample_listing_data, httpx_mock):
        """Test successful listings retrieval."""
        # Mock successful API response
        httpx_mock.add_response(
            method="GET",
            url="https://api.wheelhouse.test/listings",
            json=sample_listing_data,
            status_code=200
        )
        
        result = client.get_listings("2025-01-01", limit=50)
        
        assert result == sample_listing_data
        assert len(result["listings"]) == 2
        assert result["total"] == 2
    
    @pytest.mark.asyncio
    async def test_get_listings_with_filters(self, client, sample_listing_data, httpx_mock):
        """Test listings retrieval with filters."""
        httpx_mock.add_response(
            method="GET", 
            url="https://api.wheelhouse.test/listings",
            json=sample_listing_data,
            status_code=200
        )
        
        filters = {"property_type": "apartment", "min_price": 100}
        result = client.get_listings("2025-01-01", filters=filters)
        
        assert result == sample_listing_data
        
        # Verify request was made with correct parameters
        request = httpx_mock.get_request()
        assert "property_type=apartment" in str(request.url)
        assert "min_price=100" in str(request.url)
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, client, httpx_mock):
        """Test handling of 429 rate limit responses."""
        # First request returns rate limit
        httpx_mock.add_response(
            method="GET",
            url="https://api.wheelhouse.test/listings",
            status_code=429,
            headers={"Retry-After": "2"},
            json={"error": "Rate limit exceeded"}
        )
        
        # Second request succeeds
        httpx_mock.add_response(
            method="GET",
            url="https://api.wheelhouse.test/listings", 
            json={"listings": [], "total": 0},
            status_code=200
        )
        
        # The retry mechanism should handle the rate limit
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = client.get_listings("2025-01-01")
            
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, client, httpx_mock):
        """Test handling of API errors."""
        httpx_mock.add_response(
            method="GET",
            url="https://api.wheelhouse.test/listings",
            status_code=400,
            json={"error": "Invalid date format"}
        )
        
        with pytest.raises(WheelhouseAPIError, match="Invalid date format"):
            client.get_listings("invalid-date")
    
    @pytest.mark.asyncio
    async def test_get_all_listings_pagination(self, client, httpx_mock):
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
        
        httpx_mock.add_response(
            method="GET",
            url="https://api.wheelhouse.test/listings",
            json=page1_data,
            status_code=200
        )
        
        httpx_mock.add_response(
            method="GET", 
            url="https://api.wheelhouse.test/listings",
            json=page2_data,
            status_code=200
        )
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            all_listings = client.get_all_listings_for_date("2025-01-01", batch_size=50)
        
        assert len(all_listings) == 75
        assert all_listings[0]["id"] == "listing_0"
        assert all_listings[-1]["id"] == "listing_74"
    
    @pytest.mark.asyncio
    async def test_get_listing_details(self, client, httpx_mock):
        """Test getting detailed listing information."""
        listing_detail = {
            "id": "listing_123",
            "name": "Luxury Condo",
            "description": "A beautiful luxury condo...",
            "amenities": ["wifi", "kitchen", "parking"],
            "reviews": []
        }
        
        httpx_mock.add_response(
            method="GET",
            url="https://api.wheelhouse.test/listings/listing_123",
            json=listing_detail,
            status_code=200
        )
        
        result = client.get_listing_details("listing_123")
        
        assert result == listing_detail
        assert result["id"] == "listing_123"
        assert "amenities" in result
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client, httpx_mock):
        """Test successful health check."""
        httpx_mock.add_response(
            method="GET",
            url="https://api.wheelhouse.test/health",
            json={"status": "ok"},
            status_code=200
        )
        
        result = client.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client, httpx_mock):
        """Test health check failure."""
        httpx_mock.add_response(
            method="GET",
            url="https://api.wheelhouse.test/health",
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
        
        # Check timeout
        assert session.timeout == 10.0
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, client, httpx_mock):
        """Test behavior when all retries are exhausted."""
        # All requests return rate limit
        for _ in range(6):  # More than max retries
            httpx_mock.add_response(
                method="GET",
                url="https://api.wheelhouse.test/listings",
                status_code=429,
                headers={"Retry-After": "1"}
            )
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(WheelhouseRateLimitError):
                client.get_listings("2025-01-01")
    
    @pytest.mark.asyncio
    async def test_empty_response_handling(self, client, httpx_mock):
        """Test handling of empty responses."""
        httpx_mock.add_response(
            method="GET",
            url="https://api.wheelhouse.test/listings",
            json={"listings": [], "total": 0},
            status_code=200
        )
        
        all_listings = client.get_all_listings_for_date("2025-01-01")
        assert all_listings == []
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, client, httpx_mock):
        """Test handling of network errors."""
        httpx_mock.add_exception(httpx.ConnectError("Connection failed"))
        
        with pytest.raises(WheelhouseAPIError, match="Request failed"):
            client.get_listings("2025-01-01")
