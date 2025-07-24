"""
Health monitoring system for ETL data pipeline.

This module provides health checks and reporting capabilities for monitoring
the state of the data pipeline and storage.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from .config import Config

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors health and status of the ETL data pipeline."""

    def __init__(self, config: Config):
        """
        Initialize the health monitor.

        Args:
            config: Configuration object
        """
        self.config = config
        self.data_base_path = Path(config.data_base_path)

        logger.info("Health monitor initialized")

    def scan_data_files(self) -> list[dict[str, Any]]:
        """
        Scan all data files and collect metadata.

        Returns:
            List of file metadata dictionaries
        """
        files_info = []
        raw_data_path = self.data_base_path / "raw"

        if not raw_data_path.exists():
            logger.warning(f"Raw data path does not exist: {raw_data_path}")
            return files_info

        logger.info(f"Scanning data files in {raw_data_path}")

        # Scan all parquet files
        for parquet_file in raw_data_path.rglob("*.parquet"):
            try:
                # Get file stats
                stat = parquet_file.stat()

                # Extract listing_id and date from path
                # Expected structure: raw/{listing_id}/{date}.parquet
                parts = parquet_file.parts
                if len(parts) >= 2:
                    listing_id = parts[-2]
                    date_str = parquet_file.stem  # filename without extension
                else:
                    listing_id = "unknown"
                    date_str = "unknown"

                # Read parquet metadata (row count)
                try:
                    df = pd.read_parquet(parquet_file)
                    row_count = len(df)
                    columns = list(df.columns)
                except Exception as e:
                    logger.warning(f"Could not read parquet file {parquet_file}: {e}")
                    row_count = -1
                    columns = []

                file_info = {
                    "file_path": str(parquet_file.relative_to(self.data_base_path)),
                    "listing_id": listing_id,
                    "date": date_str,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "row_count": row_count,
                    "column_count": len(columns),
                    "columns": columns,
                }

                files_info.append(file_info)

            except Exception as e:
                logger.error(f"Error processing file {parquet_file}: {e}")
                continue

        logger.info(f"Scanned {len(files_info)} data files")
        return files_info

    def calculate_summary_stats(
        self, files_info: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Calculate summary statistics from file information.

        Args:
            files_info: List of file metadata

        Returns:
            Summary statistics dictionary
        """
        if not files_info:
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "total_rows": 0,
                "unique_listings": 0,
                "date_range": {"earliest": None, "latest": None},
                "avg_file_size_mb": 0,
                "avg_rows_per_file": 0,
            }

        # Basic counts
        total_files = len(files_info)
        total_size_bytes = sum(f["size_bytes"] for f in files_info)
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)
        total_rows = sum(f["row_count"] for f in files_info if f["row_count"] > 0)

        # Unique listings
        unique_listings = len(
            {f["listing_id"] for f in files_info if f["listing_id"] != "unknown"}
        )

        # Date range
        valid_dates = [f["date"] for f in files_info if f["date"] != "unknown"]
        if valid_dates:
            valid_dates.sort()
            date_range = {"earliest": valid_dates[0], "latest": valid_dates[-1]}
        else:
            date_range = {"earliest": None, "latest": None}

        # Averages
        avg_file_size_mb = (
            round(total_size_mb / total_files, 2) if total_files > 0 else 0
        )
        valid_row_counts = [f["row_count"] for f in files_info if f["row_count"] > 0]
        avg_rows_per_file = (
            round(sum(valid_row_counts) / len(valid_row_counts), 1)
            if valid_row_counts
            else 0
        )

        return {
            "total_files": total_files,
            "total_size_bytes": total_size_bytes,
            "total_size_mb": total_size_mb,
            "total_rows": total_rows,
            "unique_listings": unique_listings,
            "date_range": date_range,
            "avg_file_size_mb": avg_file_size_mb,
            "avg_rows_per_file": avg_rows_per_file,
        }

    def check_data_freshness(self, files_info: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Check data freshness and identify any gaps.

        Args:
            files_info: List of file metadata

        Returns:
            Data freshness analysis
        """
        # Get unique dates
        dates = {f["date"] for f in files_info if f["date"] != "unknown"}

        if not dates:
            return {
                "has_data": False,
                "latest_date": None,
                "days_since_latest": None,
                "missing_recent_dates": [],
                "data_gaps": [],
            }

        # Convert to datetime objects for analysis
        date_objects = []
        for date_str in dates:
            try:
                date_objects.append(datetime.strptime(date_str, "%Y-%m-%d").date())
            except ValueError:
                continue

        if not date_objects:
            return {
                "has_data": True,
                "latest_date": None,
                "days_since_latest": None,
                "missing_recent_dates": [],
                "data_gaps": [],
            }

        date_objects.sort()
        latest_date = date_objects[-1]
        today = datetime.now().date()
        days_since_latest = (today - latest_date).days

        # Check for missing recent dates (last 7 days)
        missing_recent = []
        for i in range(1, 8):  # Check last 7 days
            check_date = today - timedelta(days=i)
            if check_date not in date_objects:
                missing_recent.append(check_date.strftime("%Y-%m-%d"))

        # Find data gaps (missing dates in the range)
        if len(date_objects) > 1:
            data_gaps = []
            start_date = date_objects[0]
            end_date = date_objects[-1]

            current_date = start_date
            while current_date <= end_date:
                if current_date not in date_objects:
                    data_gaps.append(current_date.strftime("%Y-%m-%d"))
                current_date += timedelta(days=1)
        else:
            data_gaps = []

        return {
            "has_data": True,
            "latest_date": latest_date.strftime("%Y-%m-%d"),
            "days_since_latest": days_since_latest,
            "missing_recent_dates": missing_recent,
            "data_gaps": data_gaps[:10],  # Limit to first 10 gaps
            "total_gaps": len(data_gaps),
        }

    def analyze_listing_coverage(
        self, files_info: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Analyze listing coverage across dates.

        Args:
            files_info: List of file metadata

        Returns:
            Listing coverage analysis
        """
        # Group files by listing_id
        listings_by_id = {}
        for file_info in files_info:
            listing_id = file_info["listing_id"]
            if listing_id == "unknown":
                continue

            if listing_id not in listings_by_id:
                listings_by_id[listing_id] = []

            listings_by_id[listing_id].append(file_info)

        if not listings_by_id:
            return {
                "total_listings": 0,
                "avg_dates_per_listing": 0,
                "listings_with_single_date": 0,
                "most_active_listings": [],
                "recent_listings": [],
            }

        # Calculate statistics
        dates_per_listing = [len(files) for files in listings_by_id.values()]
        avg_dates = round(sum(dates_per_listing) / len(dates_per_listing), 1)
        single_date_count = sum(1 for count in dates_per_listing if count == 1)

        # Find most active listings (most dates)
        most_active = sorted(
            [(listing_id, len(files)) for listing_id, files in listings_by_id.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        # Find recently active listings (latest date)
        recent_listings = []
        for listing_id, files in listings_by_id.items():
            latest_file = max(
                files,
                key=lambda f: f["date"] if f["date"] != "unknown" else "0000-00-00",
            )
            if latest_file["date"] != "unknown":
                recent_listings.append((listing_id, latest_file["date"]))

        recent_listings.sort(key=lambda x: x[1], reverse=True)
        recent_listings = recent_listings[:5]

        return {
            "total_listings": len(listings_by_id),
            "avg_dates_per_listing": avg_dates,
            "listings_with_single_date": single_date_count,
            "most_active_listings": [
                {"listing_id": lid, "date_count": count} for lid, count in most_active
            ],
            "recent_listings": [
                {"listing_id": lid, "latest_date": date}
                for lid, date in recent_listings
            ],
        }

    def generate_report(self) -> dict[str, Any]:
        """
        Generate comprehensive health report.

        Returns:
            Complete health report dictionary
        """
        logger.info("Generating health report")

        # Scan all files
        files_info = self.scan_data_files()

        # Calculate various metrics
        summary = self.calculate_summary_stats(files_info)
        freshness = self.check_data_freshness(files_info)
        coverage = self.analyze_listing_coverage(files_info)

        # System information
        import sys

        system_info = {
            "data_base_path": str(self.data_base_path),
            "report_generated_at": datetime.utcnow().isoformat(),
            "python_version": f"{sys.version}",
        }

        # Health status determination
        health_status = "healthy"
        issues = []

        if summary["total_files"] == 0:
            health_status = "critical"
            issues.append("No data files found")
        elif freshness["days_since_latest"] and freshness["days_since_latest"] > 2:
            health_status = "warning"
            issues.append(f"Data is {freshness['days_since_latest']} days old")
        elif len(freshness.get("missing_recent_dates", [])) > 3:
            health_status = "warning"
            issues.append("Multiple recent dates missing")

        report = {
            "health_status": health_status,
            "issues": issues,
            "system_info": system_info,
            "summary": summary,
            "data_freshness": freshness,
            "listing_coverage": coverage,
            "files_sample": files_info[:5],  # Include sample of files
        }

        logger.info(
            f"Health report generated: {health_status} status with {len(issues)} issues"
        )
        return report

    def write_report(self, report: dict[str, Any], output_path: str) -> None:
        """
        Write health report to file.

        Args:
            report: Health report dictionary
            output_path: Path to write the report
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Health report written to {output_file}")

    def get_quick_status(self) -> str:
        """
        Get a quick health status string.

        Returns:
            Simple status string
        """
        try:
            files_info = self.scan_data_files()
            summary = self.calculate_summary_stats(files_info)
            freshness = self.check_data_freshness(files_info)

            if summary["total_files"] == 0:
                return "❌ No data files found"
            elif freshness["days_since_latest"] and freshness["days_since_latest"] > 2:
                return f"⚠️  Data is {freshness['days_since_latest']} days old"
            else:
                return (
                    f"✅ Healthy ({summary['total_files']} files, "
                    f"latest: {freshness['latest_date']})"
                )

        except Exception as e:
            return f"❌ Health check failed: {e}"
