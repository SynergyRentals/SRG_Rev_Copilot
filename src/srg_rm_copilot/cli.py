"""
Command-line interface for SRG RM Copilot.

This module defines the Typer-based CLI for the application.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from pytz import timezone

from .config import Config
from .etl import ETLProcessor
from .health import HealthMonitor
from .utils import setup_logging

app = typer.Typer(
    name="srg-rm-copilot",
    help="Production-ready Python package + CLI + ETL for Wheelhouse data with AI automation",
    no_args_is_help=True,
)

# Global config instance
config = Config()


def get_default_date() -> str:
    """Get yesterday's date in America/Chicago timezone."""
    chicago_tz = timezone("America/Chicago")
    chicago_now = datetime.now(chicago_tz)
    yesterday = chicago_now - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


@app.command()
def etl(
    date: Optional[str] = typer.Option(
        None,
        "--date",
        help="Date to process (YYYY-MM-DD). Default: yesterday in America/Chicago timezone"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be processed without writing files"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    ),
) -> None:
    """
    Run ETL process to extract Wheelhouse data and save as Parquet files.
    
    Examples:
        python -m srg_rm_copilot etl
        python -m srg_rm_copilot etl --date 2025-07-01
        python -m srg_rm_copilot etl --date 2025-07-01 --dry-run
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    # Use default date if not provided
    if date is None:
        date = get_default_date()
        logger.info(f"Using default date: {date}")
    
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        typer.echo(f"Error: Invalid date format '{date}'. Use YYYY-MM-DD.", err=True)
        raise typer.Exit(1)
    
    logger.info(f"Starting ETL process for date: {date}")
    if dry_run:
        logger.info("DRY RUN MODE: No files will be written")
    
    try:
        # Initialize ETL processor
        etl_processor = ETLProcessor(config)
        
        # Run ETL
        result = etl_processor.process_date(date, dry_run=dry_run)
        
        # Report results
        if dry_run:
            typer.echo(f"\nDRY RUN - Would process {result['total_listings']} listings:")
            for i, path in enumerate(result.get('file_paths', [])[:10]):
                typer.echo(f"  {i+1}. {path}")
            if len(result.get('file_paths', [])) > 10:
                typer.echo(f"  ... and {len(result['file_paths']) - 10} more files")
        else:
            typer.echo(f"\nETL completed successfully!")
            typer.echo(f"Processed {result['total_listings']} listings")
            typer.echo(f"Created {result['files_written']} parquet files")
            typer.echo(f"Data written to: {result['base_path']}")
    
    except Exception as e:
        logger.error(f"ETL process failed: {e}")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def health(
    output_file: Optional[str] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path for health report (default: data/health.json)"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    ),
) -> None:
    """
    Generate health report for the data pipeline.
    
    Examples:
        python -m srg_rm_copilot health
        python -m srg_rm_copilot health --output /tmp/health.json
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("Generating health report")
    
    try:
        # Initialize health monitor
        health_monitor = HealthMonitor(config)
        
        # Generate report
        report = health_monitor.generate_report()
        
        # Determine output file
        if output_file is None:
            output_file = "data/health.json"
        
        # Write report
        health_monitor.write_report(report, output_file)
        
        typer.echo(f"Health report generated: {output_file}")
        typer.echo(f"Total files: {report['summary']['total_files']}")
        typer.echo(f"Total size: {report['summary']['total_size_mb']:.2f} MB")
        typer.echo(f"Date range: {report['summary']['date_range']['earliest']} to {report['summary']['date_range']['latest']}")
    
    except Exception as e:
        logger.error(f"Health report generation failed: {e}")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def config_check() -> None:
    """
    Check configuration and API connectivity.
    
    Examples:
        python -m srg_rm_copilot config-check
    """
    setup_logging(logging.INFO)
    logger = logging.getLogger(__name__)
    
    typer.echo("Checking configuration...")
    
    # Check required environment variables
    missing_vars = []
    if not config.wheelhouse_api_key:
        missing_vars.append("WHEELHOUSE_API_KEY")
    if not config.wheelhouse_user_api_key:
        missing_vars.append("WHEELHOUSE_USER_API_KEY")
    
    if missing_vars:
        typer.echo(f"❌ Missing required environment variables: {', '.join(missing_vars)}", err=True)
        typer.echo("\nPlease set the following environment variables:")
        for var in missing_vars:
            typer.echo(f"  export {var}='your_key_here'")
        raise typer.Exit(1)
    
    typer.echo("✅ Required environment variables are set")
    
    # Test Wheelhouse API connectivity
    try:
        from .wheelhouse import WheelhouseClient
        client = WheelhouseClient(config)
        
        # This would be a simple connectivity test
        # For now, just check that client initializes
        typer.echo("✅ Wheelhouse client initialized successfully")
        
    except Exception as e:
        typer.echo(f"❌ Wheelhouse client error: {e}", err=True)
        raise typer.Exit(1)
    
    # Check data directory
    data_dir = Path(config.data_base_path)
    if not data_dir.exists():
        typer.echo(f"⚠️  Data directory does not exist: {data_dir}")
        typer.echo("It will be created when ETL runs.")
    else:
        typer.echo(f"✅ Data directory exists: {data_dir}")
    
    # Check OpenAI API key (optional)
    if config.openai_api_key:
        typer.echo("✅ OpenAI API key is set (AI features available)")
    else:
        typer.echo("⚠️  OpenAI API key not set (AI features disabled)")
    
    typer.echo("\n🎉 Configuration check completed!")


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit"
    )
) -> None:
    """SRG RM Copilot - Production-ready ETL and AI automation for Wheelhouse data."""
    if version:
        from . import __version__
        typer.echo(f"srg-rm-copilot {__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
