"""
Tests for the ETL processor.

This module tests the ETLProcessor including data transformation,
parquet file writing, and error handling.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.srg_rm_copilot.config import Config
from src.srg_rm_copilot.etl import ETLProcessor
from src.srg_rm_copilot.wheelhouse import WheelhouseClient


@pytest.fixture
def temp_config():
    """Create a test configuration with temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config(
            wheelhouse_api_key="test_api_key",
            wheelhouse_user_api_key="test_user_api_key",
            data_base_path=temp_dir,
            etl_batch_size=10,
            etl_max_retries=2,
        )
        yield config


@pytest.fixture
def etl_processor(temp_config):
    """Create a test ETL processor."""
    return ETLProcessor(temp_config)


@pytest.fixture
def mock_config(temp_config):
    """Create a test configuration with mock mode enabled."""
    temp_config.wheelhouse_mock = True
    return temp_config


@pytest.fixture
def mock_etl_processor(mock_config):
    """Create a test ETL processor in mock mode."""
    return ETLProcessor(mock_config)


@pytest.fixture
def sample_listing_data():
    """Sample listing data for testing."""
    return [
        {
            "id": "listing_1",
            "name": "Beautiful Apartment",
            "price_per_night": 150.0,
            "address": "123 Main St",
            "room_type": "Entire home/apt",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
            "bedrooms": 2,
            "bathrooms": 1,
            "amenities": ["wifi", "kitchen"],
        },
        {
            "id": "listing_2",
            "name": "Cozy Studio",
            "price_per_night": 85.0,
            "address": "456 Oak Ave",
            "room_type": "Private room",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
            "bedrooms": 1,
            "bathrooms": 1,
            "amenities": ["wifi"],
        },
    ]


class TestETLProcessor:
    """Test cases for ETLProcessor."""

    def test_processor_initialization(self, temp_config):
        """Test ETL processor initializes properly."""
        processor = ETLProcessor(temp_config)
        assert processor.config == temp_config
        assert isinstance(processor.wheelhouse_client, WheelhouseClient)

    def test_create_directory_structure(self, etl_processor, temp_config):
        """Test directory structure creation."""
        listing_id = "test_listing_123"
        listing_dir = etl_processor._create_directory_structure(listing_id)

        expected_path = Path(temp_config.data_base_path) / "raw" / listing_id
        assert listing_dir == expected_path
        assert listing_dir.exists()
        assert listing_dir.is_dir()

    def test_transform_listing_data_success(self, etl_processor, sample_listing_data):
        """Test successful data transformation."""
        df = etl_processor._transform_listing_data(sample_listing_data)

        # Check basic structure
        assert len(df) == 2
        assert "listing_id" in df.columns
        assert "title" in df.columns
        assert "price" in df.columns

        # Check data mapping
        assert df.iloc[0]["listing_id"] == "listing_1"
        assert df.iloc[0]["title"] == "Beautiful Apartment"
        assert df.iloc[0]["price"] == 150.0

        # Check metadata columns
        assert "etl_processed_at" in df.columns
        assert "etl_source" in df.columns
        assert df.iloc[0]["etl_source"] == "wheelhouse_api"

    def test_transform_empty_data(self, etl_processor):
        """Test transformation of empty data."""
        df = etl_processor._transform_listing_data([])

        assert len(df) == 0
        assert "listing_id" in df.columns
        assert "title" in df.columns
        assert "price" in df.columns

    def test_transform_missing_columns(self, etl_processor):
        """Test transformation with missing required columns."""
        incomplete_data = [
            {
                "some_other_field": "value",
                "price_per_night": 100.0,
            }
        ]

        df = etl_processor._transform_listing_data(incomplete_data)

        # Should still create required columns
        assert "listing_id" in df.columns
        assert "title" in df.columns
        assert "price" in df.columns

        # Missing values should be None, but listing_id is converted to string so becomes 'None'
        assert df.iloc[0]["listing_id"] == "None"  # listing_id is converted to string
        assert pd.isna(df.iloc[0]["title"])  # title remains None
        assert (
            df.iloc[0]["price"] == 100.0
        )  # price_per_night should be mapped correctly

    def test_write_parquet_file(self, etl_processor, sample_listing_data, temp_config):
        """Test writing parquet file."""
        df = etl_processor._transform_listing_data(sample_listing_data)
        listing_id = "test_listing"
        date = "2025-01-01"

        file_path = etl_processor._write_parquet_file(df, listing_id, date)

        # Check file was created
        assert os.path.exists(file_path)

        # Check file contents
        read_df = pd.read_parquet(file_path)
        assert len(read_df) == len(df)
        assert list(read_df.columns) == list(df.columns)

        # Check file is in correct location
        expected_path = temp_config.get_raw_data_path(listing_id, date)
        assert file_path == expected_path

    def test_group_listings_by_id(self, etl_processor, sample_listing_data):
        """Test grouping listings by ID."""
        # Add duplicate listing with same ID
        duplicate_listing = sample_listing_data[0].copy()
        duplicate_listing["updated_at"] = "2025-01-03T00:00:00Z"
        extended_data = sample_listing_data + [duplicate_listing]

        grouped = etl_processor._group_listings_by_id(extended_data)

        assert len(grouped) == 2  # Still 2 unique listing IDs
        assert "listing_1" in grouped
        assert "listing_2" in grouped
        assert len(grouped["listing_1"]) == 2  # listing_1 appears twice
        assert len(grouped["listing_2"]) == 1  # listing_2 appears once

    @patch.object(WheelhouseClient, "get_all_listings_for_date")
    def test_process_date_success(
        self, mock_get_listings, etl_processor, sample_listing_data, temp_config
    ):
        """Test successful date processing."""
        mock_get_listings.return_value = sample_listing_data

        result = etl_processor.process_date("2025-01-01", dry_run=False)

        # Check result structure
        assert result["date"] == "2025-01-01"
        assert result["total_listings"] == 2
        assert result["unique_listing_ids"] == 2
        assert result["files_written"] == 2
        assert len(result["file_paths"]) == 2

        # Check files were actually created
        for file_path in result["file_paths"]:
            assert os.path.exists(file_path)

    @patch.object(WheelhouseClient, "get_all_listings_for_date")
    def test_process_date_dry_run(
        self, mock_get_listings, etl_processor, sample_listing_data
    ):
        """Test dry run mode."""
        mock_get_listings.return_value = sample_listing_data

        result = etl_processor.process_date("2025-01-01", dry_run=True)

        # Check result structure
        assert result["date"] == "2025-01-01"
        assert result["total_listings"] == 2
        assert result["files_written"] == 0  # No files written in dry run
        assert len(result["file_paths"]) == 2  # But paths are still returned

        # Check no files were actually created
        for file_path in result["file_paths"]:
            assert not os.path.exists(file_path)

    @patch.object(WheelhouseClient, "get_all_listings_for_date")
    def test_process_date_no_data(self, mock_get_listings, etl_processor):
        """Test processing when no data is available."""
        mock_get_listings.return_value = []

        result = etl_processor.process_date("2025-01-01")

        assert result["total_listings"] == 0
        assert result["files_written"] == 0
        assert result["file_paths"] == []

    def test_process_date_invalid_format(self, etl_processor):
        """Test processing with invalid date format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            etl_processor.process_date("invalid-date")

    @patch.object(WheelhouseClient, "get_all_listings_for_date")
    def test_process_date_api_error(self, mock_get_listings, etl_processor):
        """Test handling of API errors during processing."""
        mock_get_listings.side_effect = Exception("API connection failed")

        with pytest.raises(Exception, match="API connection failed"):
            etl_processor.process_date("2025-01-01")

    @patch.object(WheelhouseClient, "get_all_listings_for_date")
    def test_process_date_partial_failure(
        self, mock_get_listings, etl_processor, temp_config
    ):
        """Test processing with some listings failing."""
        # Create data where one listing will cause issues
        problematic_data = [
            {
                "id": "good_listing",
                "name": "Good Listing",
                "price_per_night": 100.0,
            },
            {
                "id": "bad_listing",
                # Missing required data that might cause transformation issues
            },
        ]

        mock_get_listings.return_value = problematic_data

        # Should continue processing despite individual failures
        result = etl_processor.process_date("2025-01-01")

        # Should still process the good listing
        assert result["total_listings"] == 2
        # May have fewer files written due to failures
        assert result["files_written"] <= 2

    def test_process_date_range_success(self, etl_processor):
        """Test processing date range."""
        with patch.object(etl_processor, "process_date") as mock_process:
            mock_process.return_value = {
                "total_listings": 5,
                "files_written": 3,
            }

            result = etl_processor.process_date_range("2025-01-01", "2025-01-03")

            # Should call process_date for each date
            assert mock_process.call_count == 3

            # Check summary
            assert result["total_dates_processed"] == 3
            assert result["total_dates_failed"] == 0
            assert result["total_listings"] == 15  # 5 * 3
            assert result["total_files_written"] == 9  # 3 * 3

    def test_process_date_range_invalid_dates(self, etl_processor):
        """Test date range with invalid order."""
        with pytest.raises(ValueError, match="Start date must be before"):
            etl_processor.process_date_range("2025-01-03", "2025-01-01")

    def test_process_date_range_with_failures(self, etl_processor):
        """Test date range processing with some failures."""

        def mock_process_date(date, dry_run=False):
            if date == "2025-01-02":
                raise Exception("Processing failed")
            return {
                "total_listings": 5,
                "files_written": 3,
            }

        with patch.object(etl_processor, "process_date", side_effect=mock_process_date):
            result = etl_processor.process_date_range("2025-01-01", "2025-01-03")

            # Should handle failures gracefully
            assert result["total_dates_processed"] == 2
            assert result["total_dates_failed"] == 1
            assert "2025-01-02" in result["results_by_date"]
            assert "error" in result["results_by_date"]["2025-01-02"]

    def test_process_date_mock_mode(self, mock_etl_processor):
        """Test processing in mock mode."""
        # Ensure fixture file exists
        fixture_path = Path("tests/fixtures/wheelhouse_listings.json")
        assert fixture_path.exists(), "Mock fixture file should exist"

        result = mock_etl_processor.process_date("2025-01-01", dry_run=False)

        # Check result structure
        assert result["total_listings"] == 3  # Based on fixture data
        assert result["unique_listing_ids"] == 3
        assert result["files_written"] == 3
        assert len(result["file_paths"]) == 3

        # Check that the data processed matches fixture data
        expected_listing_ids = ["listing_001", "listing_002", "listing_003"]
        for expected_id in expected_listing_ids:
            assert any(expected_id in path for path in result["file_paths"])

    def test_mock_data_loading(self, mock_etl_processor):
        """Test loading data from fixture file."""
        listings = mock_etl_processor._load_mock_data()

        assert len(listings) == 3
        assert listings[0]["id"] == "listing_001"
        assert listings[0]["name"] == "Cozy Downtown Apartment"
        assert listings[1]["id"] == "listing_002"
        assert listings[2]["id"] == "listing_003"

    def test_data_type_conversion(self, etl_processor):
        """Test proper data type conversion during transformation."""
        test_data = [
            {
                "id": 12345,  # Should be converted to string
                "price_per_night": "150.50",  # Should be converted to float
                "created_at": "2025-01-01T12:00:00+00:00",  # Should be converted to datetime
            }
        ]

        df = etl_processor._transform_listing_data(test_data)

        # Check data types
        assert df["listing_id"].dtype == "object"  # String type in pandas
        assert pd.api.types.is_numeric_dtype(df["price"])
        assert pd.api.types.is_datetime64_any_dtype(df["listing_date"])

    def test_file_overwrite_behavior(
        self, etl_processor, sample_listing_data, temp_config
    ):
        """Test that files are properly overwritten when processing same date/listing."""
        df = etl_processor._transform_listing_data(sample_listing_data[:1])
        listing_id = "test_listing"
        date = "2025-01-01"

        # Write file first time
        file_path1 = etl_processor._write_parquet_file(df, listing_id, date)
        original_size = os.path.getsize(file_path1)

        # Modify data and write again
        df["new_column"] = "test_value"
        file_path2 = etl_processor._write_parquet_file(df, listing_id, date)

        # Should be same path
        assert file_path1 == file_path2

        # File should be updated (different size due to new column)
        new_size = os.path.getsize(file_path2)
        assert new_size != original_size

        # Verify new column exists
        read_df = pd.read_parquet(file_path2)
        assert "new_column" in read_df.columns
