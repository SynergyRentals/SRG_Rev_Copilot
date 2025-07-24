"""
Wheelhouse API client with retry logic and error handling.

This module provides a robust client for interacting with the Wheelhouse API,
including automatic retries with exponential backoff for rate limiting.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from urllib3.util.retry import Retry

from .config import Config

logger = logging.getLogger(__name__)


class WheelhouseAPIError(Exception):
    """Base exception for Wheelhouse API errors."""
    pass


class WheelhouseRateLimitError(WheelhouseAPIError):
    """Exception raised when hitting rate limits."""
    pass


class WheelhouseClient:
    """Client for interacting with the Wheelhouse API."""
    
    def __init__(self, config: Config):
        """
        Initialize the Wheelhouse client.
        
        Args:
            config: Configuration object containing API keys and settings
        """
        self.config = config
        self.base_url = config.wheelhouse_base_url.rstrip("/")
        
        # Validate required configuration
        config.validate_required_keys()
        
        # Setup session with retry configuration
        self.session = self._create_session()
        
        logger.info("Wheelhouse client initialized")
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry configuration."""
        session = requests.Session()
        
        # Configure retry strategy for connection issues
        retry_strategy = Retry(
            total=self.config.etl_max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update(self.config.wheelhouse_headers)
        
        # Set timeout
        session.timeout = self.config.etl_timeout
        
        return session
    
    @retry(
        retry=retry_if_exception_type(WheelhouseRateLimitError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        reraise=True
    )
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """
        Make a request to the Wheelhouse API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: JSON data for POST requests
            
        Returns:
            Response object
            
        Raises:
            WheelhouseRateLimitError: When rate limited (429)
            WheelhouseAPIError: For other API errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        logger.debug(f"Making {method} request to {url}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                logger.warning(f"Rate limited. Retry after {retry_after} seconds")
                raise WheelhouseRateLimitError(f"Rate limited. Retry after {retry_after} seconds")
            
            # Handle other client/server errors
            if response.status_code >= 400:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg += f": {error_data['error']}"
                except Exception:
                    error_msg += f": {response.text[:200]}"
                
                logger.error(error_msg)
                raise WheelhouseAPIError(error_msg)
            
            logger.debug(f"Request successful: {response.status_code}")
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise WheelhouseAPIError(f"Request failed: {e}")
    
    def get_listings(
        self,
        date: str,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get listings for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
            limit: Number of listings to retrieve (max 100)
            offset: Offset for pagination
            filters: Additional filters to apply
            
        Returns:
            API response containing listings data
        """
        params = {
            "date": date,
            "limit": min(limit, 100),  # Ensure we don't exceed API limits
            "offset": offset,
        }
        
        if filters:
            params.update(filters)
        
        logger.info(f"Fetching listings for date {date} (limit={limit}, offset={offset})")
        
        response = self._make_request("GET", "/listings", params=params)
        data = response.json()
        
        logger.info(f"Retrieved {len(data.get('listings', []))} listings")
        return data
    
    def get_all_listings_for_date(
        self,
        date: str,
        batch_size: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all listings for a specific date using pagination.
        
        Args:
            date: Date in YYYY-MM-DD format
            batch_size: Number of listings per batch (default: config.etl_batch_size)
            filters: Additional filters to apply
            
        Returns:
            List of all listings for the date
        """
        if batch_size is None:
            batch_size = self.config.etl_batch_size
        
        all_listings = []
        offset = 0
        total_fetched = 0
        
        logger.info(f"Starting to fetch all listings for date {date}")
        
        while True:
            try:
                data = self.get_listings(
                    date=date,
                    limit=batch_size,
                    offset=offset,
                    filters=filters
                )
                
                listings = data.get("listings", [])
                if not listings:
                    break
                
                all_listings.extend(listings)
                total_fetched += len(listings)
                offset += batch_size
                
                # Check if we've reached the total
                total_available = data.get("total", 0)
                if total_fetched >= total_available:
                    break
                
                logger.debug(f"Fetched {total_fetched} of {total_available} listings")
                
                # Small delay between requests to be respectful
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error fetching listings batch at offset {offset}: {e}")
                raise
        
        logger.info(f"Successfully fetched {len(all_listings)} total listings for date {date}")
        return all_listings
    
    def get_listing_details(self, listing_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific listing.
        
        Args:
            listing_id: The ID of the listing
            
        Returns:
            Detailed listing data
        """
        logger.debug(f"Fetching details for listing {listing_id}")
        
        response = self._make_request("GET", f"/listings/{listing_id}")
        return response.json()
    
    def health_check(self) -> bool:
        """
        Perform a health check against the Wheelhouse API.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Make a simple request to check connectivity
            response = self._make_request("GET", "/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
