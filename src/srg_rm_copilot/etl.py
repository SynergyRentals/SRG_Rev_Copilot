"""
ETL processor for Wheelhouse data.

This module handles the extraction, transformation, and loading of Wheelhouse data
into Parquet files with proper directory structure and error handling.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .config import Config
from .wheelhouse import WheelhouseClient

logger = logging.getLogger(__name__)


class ETLProcessor:
    """Processes ETL operations for Wheelhouse data."""

    def __init__(self, config: Config):
        """
        Initialize the ETL processor.

        Args:
            config: Configuration object
        """
        self.config = config
        self.wheelhouse_client = (
            WheelhouseClient(config) if not config.wheelhouse_mock else None
        )

        if config.wheelhouse_mock:
            logger.info("ETL processor initialized in MOCK mode")
        else:
            logger.info("ETL processor initialized")

    def _create_directory_structure(self, listing_id: str) -> Path:
        """
        Create directory structure for a listing.

        Args:
            listing_id: The listing ID

        Returns:
            Path object for the listing directory
        """
        listing_dir = Path(self.config.data_base_path) / "raw" / listing_id
        listing_dir.mkdir(parents=True, exist_ok=True)
        return listing_dir

    def _transform_listing_data(self, listings: list[dict[str, Any]]) -> pd.DataFrame:
        """
        Transform raw listing data into a structured DataFrame.

        Args:
            listings: List of raw listing data from API

        Returns:
            Transformed DataFrame ready for Parquet storage
        """
        if not listings:
            # Return empty DataFrame with expected schema
            columns = [
                "listing_id",
                "title",
                "price",
                "location",
                "bedrooms",
                "bathrooms",
                "property_type",
                "listing_date",
                "last_updated",
                "amenities",
                "description",
                "host_id",
                "availability",
                "minimum_stay",
                "maximum_stay",
                "instant_book",
                "cancellation_policy",
                "review_score",
                "review_count",
                "latitude",
                "longitude",
            ]
            return pd.DataFrame(columns=columns)

        # Convert to DataFrame
        df = pd.DataFrame(listings)

        # Ensure consistent column names and types
        column_mapping = {
            "id": "listing_id",
            "name": "title",
            "price_per_night": "price",
            "address": "location",
            "room_type": "property_type",
            "created_at": "listing_date",
            "updated_at": "last_updated",
        }

        # Rename columns if they exist
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df.rename(columns={old_name: new_name}, inplace=True)

        # Ensure required columns exist
        required_columns = ["listing_id", "title", "price"]
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"Required column '{col}' not found in data")
                df[col] = None

        # Convert data types
        if "listing_id" in df.columns:
            df["listing_id"] = df["listing_id"].astype(str)

        if "price" in df.columns:
            df["price"] = pd.to_numeric(df["price"], errors="coerce")

        # Handle datetime columns
        for date_col in ["listing_date", "last_updated"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        # Add processing metadata
        df["etl_processed_at"] = datetime.utcnow()
        df["etl_source"] = "wheelhouse_api"

        logger.debug(f"Transformed {len(df)} listings with {len(df.columns)} columns")
        return df

    def _write_parquet_file(self, df: pd.DataFrame, listing_id: str, date: str) -> str:
        """
        Write DataFrame to Parquet file.

        Args:
            df: DataFrame to write
            listing_id: The listing ID
            date: Date string in YYYY-MM-DD format

        Returns:
            Path to the written file
        """
        listing_dir = self._create_directory_structure(listing_id)
        file_path = listing_dir / f"{date}.parquet"

        # Convert DataFrame to PyArrow Table for better control
        table = pa.Table.from_pandas(df)

        # Write with compression
        pq.write_table(
            table,
            file_path,
            compression="snappy",
            use_dictionary=True,
            row_group_size=10000,
        )

        file_size = file_path.stat().st_size
        logger.info(f"Wrote {len(df)} rows to {file_path} ({file_size:,} bytes)")

        return str(file_path)

    def _group_listings_by_id(
        self, listings: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Group listings by listing ID.

        Args:
            listings: List of listing data

        Returns:
            Dictionary mapping listing_id to list of listing data
        """
        grouped = {}

        for listing in listings:
            listing_id = str(listing.get("id", listing.get("listing_id", "unknown")))

            if listing_id not in grouped:
                grouped[listing_id] = []

            grouped[listing_id].append(listing)

        logger.debug(
            f"Grouped {len(listings)} listings into {len(grouped)} unique listing IDs"
        )
        return grouped

    def _load_mock_data(self) -> list[dict[str, Any]]:
        """
        Load mock data from fixture file.

        Returns:
            List of mock listing data
        """
        fixture_path = Path("tests/fixtures/wheelhouse_listings.json")

        if not fixture_path.exists():
            logger.error(f"Mock data fixture not found at {fixture_path}")
            raise FileNotFoundError(f"Mock data fixture not found at {fixture_path}")

        try:
            with open(fixture_path) as f:
                data = json.load(f)

            listings = data.get("listings", [])
            logger.info(f"Loaded {len(listings)} mock listings from fixture")
            return listings
        except Exception as e:
            logger.error(f"Failed to load mock data: {e}")
            raise

    def process_date(self, date: str, dry_run: bool = False) -> dict[str, Any]:
        """
        Process all listings for a specific date.

        Args:
            date: Date string in YYYY-MM-DD format
            dry_run: If True, don't write files, just return what would be processed

        Returns:
            Dictionary containing processing results
        """
        logger.info(f"Starting ETL process for date: {date} (dry_run={dry_run})")

        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {date}. Expected YYYY-MM-DD")

        try:
            # Fetch all listings for the date
            if self.config.wheelhouse_mock:
                logger.info("Loading listings from mock fixture")
                listings = self._load_mock_data()
            else:
                logger.info("Fetching listings from Wheelhouse API")
                listings = self.wheelhouse_client.get_all_listings_for_date(date)

            if not listings:
                logger.warning(f"No listings found for date {date}")
                return {
                    "date": date,
                    "total_listings": 0,
                    "files_written": 0,
                    "file_paths": [],
                    "base_path": self.config.data_base_path,
                }

            # Group listings by listing ID
            grouped_listings = self._group_listings_by_id(listings)

            file_paths = []
            files_written = 0

            # Process each listing group
            for listing_id, listing_group in grouped_listings.items():
                try:
                    # Transform data
                    df = self._transform_listing_data(listing_group)

                    if df.empty:
                        logger.warning(f"No data to write for listing {listing_id}")
                        continue

                    # Generate file path (even for dry run)
                    expected_path = self.config.get_raw_data_path(listing_id, date)
                    file_paths.append(expected_path)

                    if not dry_run:
                        # Write to Parquet file
                        actual_path = self._write_parquet_file(df, listing_id, date)
                        files_written += 1

                        # Verify the file was written correctly
                        if not os.path.exists(actual_path):
                            logger.error(f"Failed to write file: {actual_path}")

                except Exception as e:
                    logger.error(f"Error processing listing {listing_id}: {e}")
                    # Continue processing other listings
                    continue

            result = {
                "date": date,
                "total_listings": len(listings),
                "unique_listing_ids": len(grouped_listings),
                "files_written": files_written,
                "file_paths": file_paths,
                "base_path": self.config.data_base_path,
            }

            if dry_run:
                logger.info(
                    f"DRY RUN completed: would process {len(listings)} listings "
                    f"into {len(file_paths)} files"
                )
            else:
                logger.info(
                    f"ETL completed: processed {len(listings)} listings, "
                    f"wrote {files_written} files"
                )

            return result

        except Exception as e:
            logger.error(f"ETL process failed for date {date}: {e}")
            raise

    def process_date_range(
        self, start_date: str, end_date: str, dry_run: bool = False
    ) -> dict[str, Any]:
        """
        Process multiple dates in a range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (inclusive)
            dry_run: If True, don't write files

        Returns:
            Dictionary containing processing results for all dates
        """
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        if start_dt > end_dt:
            raise ValueError("Start date must be before or equal to end date")

        results = {}
        total_listings = 0
        total_files = 0

        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")

            try:
                result = self.process_date(date_str, dry_run=dry_run)
                results[date_str] = result
                total_listings += result["total_listings"]
                total_files += result["files_written"]

            except Exception as e:
                logger.error(f"Failed to process date {date_str}: {e}")
                results[date_str] = {"error": str(e)}

            # Move to next day
            current_dt = current_dt.replace(day=current_dt.day + 1)

        summary = {
            "date_range": f"{start_date} to {end_date}",
            "total_dates_processed": len(
                [r for r in results.values() if "error" not in r]
            ),
            "total_dates_failed": len([r for r in results.values() if "error" in r]),
            "total_listings": total_listings,
            "total_files_written": total_files,
            "results_by_date": results,
        }

        logger.info(
            f"Date range processing completed: {summary['total_dates_processed']} "
            f"successful, {summary['total_dates_failed']} failed"
        )

        return summary
