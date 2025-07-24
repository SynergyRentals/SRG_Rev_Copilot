#!/usr/bin/env python3
"""
Health check script for SRG RM Copilot.

This script generates a comprehensive health report for the ETL data pipeline
and writes it to the health.json file. It's designed to be run as a standalone
script or from GitHub Actions for nightly monitoring.

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --output /custom/path/health.json
    python scripts/health_check.py --verbose
"""

import argparse
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# noqa: E402 - Module level imports after sys.path modification
from srg_rm_copilot.config import Config  # noqa: E402
from srg_rm_copilot.health import HealthMonitor  # noqa: E402
from srg_rm_copilot.utils import setup_logging  # noqa: E402


def main():
    """Main function for the health check script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate health report for SRG RM Copilot ETL pipeline"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path for health report (default: data/health.json)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress all output except errors"
    )
    parser.add_argument(
        "--format",
        choices=["json", "summary"],
        default="json",
        help="Output format (default: json)"
    )

    args = parser.parse_args()

    # Setup logging
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    try:
        # Initialize configuration
        logger.info("Initializing configuration")
        config = Config()

        # Initialize health monitor
        logger.info("Initializing health monitor")
        health_monitor = HealthMonitor(config)

        # Generate health report
        logger.info("Generating health report")
        report = health_monitor.generate_report()

        # Determine output file
        if args.output:
            output_file = args.output
        else:
            output_file = config.get_health_file_path()

        logger.info(f"Writing health report to {output_file}")

        # Write the report
        health_monitor.write_report(report, output_file)

        # Output results based on format
        if args.format == "summary":
            print_summary(report)
        elif not args.quiet:
            print_json_info(report, output_file)

        # Exit with appropriate code based on health status
        if report.get("health_status") == "critical":
            logger.error("Health status is CRITICAL")
            sys.exit(2)
        elif report.get("health_status") == "warning":
            logger.warning("Health status is WARNING")
            sys.exit(1)
        else:
            logger.info("Health status is HEALTHY")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        if args.verbose:
            logger.exception("Full traceback:")

        if not args.quiet:
            print(f"❌ Health check failed: {e}", file=sys.stderr)

        sys.exit(3)


def print_summary(report):
    """
    Print a human-readable summary of the health report.

    Args:
        report: Health report dictionary
    """
    status = report.get("health_status", "unknown")
    summary = report.get("summary", {})
    freshness = report.get("data_freshness", {})
    coverage = report.get("listing_coverage", {})

    # Status indicator
    status_icon = {
        "healthy": "✅",
        "warning": "⚠️ ",
        "critical": "❌",
        "unknown": "❓"
    }.get(status, "❓")

    print(f"{status_icon} Health Status: {status.upper()}")
    print()

    # Issues
    issues = report.get("issues", [])
    if issues:
        print("Issues:")
        for issue in issues:
            print(f"  • {issue}")
        print()

    # Summary statistics
    print("Data Summary:")
    print(f"  Total Files: {summary.get('total_files', 0):,}")
    print(f"  Total Size: {summary.get('total_size_mb', 0):.1f} MB")
    print(f"  Total Rows: {summary.get('total_rows', 0):,}")
    print(f"  Unique Listings: {summary.get('unique_listings', 0):,}")

    # Date range
    date_range = summary.get("date_range", {})
    if date_range.get("earliest") and date_range.get("latest"):
        print(f"  Date Range: {date_range['earliest']} to {date_range['latest']}")

    print()

    # Data freshness
    if freshness.get("has_data"):
        latest_date = freshness.get("latest_date")
        days_old = freshness.get("days_since_latest", 0)

        print("Data Freshness:")
        print(f"  Latest Data: {latest_date}")
        if days_old == 0:
            print("  Status: Current (today)")
        elif days_old == 1:
            print("  Status: Recent (1 day old)")
        elif days_old <= 3:
            print(f"  Status: Acceptable ({days_old} days old)")
        else:
            print(f"  Status: Stale ({days_old} days old)")

        missing_recent = freshness.get("missing_recent_dates", [])
        if missing_recent:
            print(f"  Missing Recent Dates: {len(missing_recent)} days")

        gaps = freshness.get("total_gaps", 0)
        if gaps > 0:
            print(f"  Data Gaps: {gaps} missing dates in range")

        print()

    # Coverage statistics
    print("Listing Coverage:")
    print(f"  Total Listings: {coverage.get('total_listings', 0):,}")
    print(f"  Avg Dates per Listing: {coverage.get('avg_dates_per_listing', 0):.1f}")

    single_date = coverage.get("listings_with_single_date", 0)
    if single_date > 0:
        print(f"  Single-Date Listings: {single_date:,}")

    # Most active listings
    most_active = coverage.get("most_active_listings", [])
    if most_active:
        print("  Most Active Listings:")
        for listing in most_active[:3]:
            print(f"    {listing['listing_id']}: {listing['date_count']} dates")

    print()

    # Report timestamp
    generated_at = report.get("system_info", {}).get("report_generated_at")
    if generated_at:
        print(f"Report generated: {generated_at}")


def print_json_info(report, output_file):
    """
    Print information about the JSON report that was written.

    Args:
        report: Health report dictionary
        output_file: Path where the report was written
    """
    status = report.get("health_status", "unknown")
    summary = report.get("summary", {})

    status_icon = {
        "healthy": "✅",
        "warning": "⚠️ ",
        "critical": "❌",
        "unknown": "❓"
    }.get(status, "❓")

    print(f"{status_icon} Health report generated: {output_file}")
    print(f"Status: {status.upper()}")
    print(f"Files: {summary.get('total_files', 0):,}")
    print(f"Size: {summary.get('total_size_mb', 0):.1f} MB")

    date_range = summary.get("date_range", {})
    if date_range.get("earliest") and date_range.get("latest"):
        print(f"Date Range: {date_range['earliest']} to {date_range['latest']}")

    # Show issues if any
    issues = report.get("issues", [])
    if issues:
        print(f"Issues: {len(issues)}")
        for issue in issues:
            print(f"  • {issue}")


if __name__ == "__main__":
    main()
