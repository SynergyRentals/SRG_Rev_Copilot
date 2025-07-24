"""
Configuration management for SRG RM Copilot.

This module handles loading and validating configuration from environment variables.
"""

import os
from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Configuration settings for SRG RM Copilot."""
    
    # Wheelhouse API Configuration
    wheelhouse_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("WHEELHOUSE_API_KEY"),
        description="Wheelhouse API key for authentication"
    )
    
    wheelhouse_user_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("WHEELHOUSE_USER_API_KEY"),
        description="Wheelhouse user API key for authentication"
    )
    
    wheelhouse_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "WHEELHOUSE_BASE_URL", 
            "https://api.usewheelhouse.com/wheelhouse_pro_api"
        ),
        description="Base URL for Wheelhouse API"
    )
    
    # Mock mode configuration
    wheelhouse_mock: bool = Field(
        default_factory=lambda: os.getenv("WHEELHOUSE_MOCK", "0") == "1",
        description="Enable mock mode to skip API calls and use fixture data"
    )
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY"),
        description="OpenAI API key for AI features"
    )
    
    openai_model: str = Field(
        default="gpt-4",
        description="OpenAI model to use for AI features"
    )
    
    # Data Storage Configuration
    data_base_path: str = Field(
        default="data",
        description="Base path for data storage"
    )
    
    # ETL Configuration
    etl_batch_size: int = Field(
        default=100,
        description="Number of listings to process per batch"
    )
    
    etl_max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed requests"
    )
    
    etl_retry_delay: float = Field(
        default=1.0,
        description="Initial delay between retries in seconds"
    )
    
    etl_timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds"
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    
    # Chicago timezone for default date calculations
    default_timezone: str = Field(
        default="America/Chicago",
        description="Default timezone for date operations"
    )
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "SRG_"
        case_sensitive = False
    
    def validate_required_keys(self) -> None:
        """Validate that required API keys are present."""
        if not self.wheelhouse_api_key:
            raise ValueError("WHEELHOUSE_API_KEY environment variable is required")
        
        if not self.wheelhouse_user_api_key:
            raise ValueError("WHEELHOUSE_USER_API_KEY environment variable is required")
    
    def get_data_path(self, *parts: str) -> str:
        """Get a path relative to the data base path."""
        return os.path.join(self.data_base_path, *parts)
    
    def get_raw_data_path(self, listing_id: str, date: str) -> str:
        """Get the path for raw data files."""
        return self.get_data_path("raw", listing_id, f"{date}.parquet")
    
    def get_health_file_path(self) -> str:
        """Get the path for the health report file."""
        return self.get_data_path("health.json")
    
    @property
    def wheelhouse_headers(self) -> dict:
        """Get headers for Wheelhouse API requests."""
        return {
            "Authorization": f"Bearer {self.wheelhouse_api_key}",
            "X-User-API-Key": self.wheelhouse_user_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
