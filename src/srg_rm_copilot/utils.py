"""
Utility functions for SRG RM Copilot.

This module contains common utility functions used throughout the application.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pytz import timezone


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    log_file: Optional[str] = None
) -> None:
    """
    Setup logging configuration.
    
    Args:
        level: Logging level (e.g., logging.INFO)
        format_string: Custom format string for log messages
        log_file: Optional file path to write logs to
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Remove any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Setup basic config
    logging.basicConfig(
        level=level,
        format=format_string,
        stream=sys.stdout
    )
    
    # Add file handler if requested
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        formatter = logging.Formatter(format_string)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set level for third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


def get_chicago_time(dt: Optional[datetime] = None) -> datetime:
    """
    Get current time or convert datetime to Chicago timezone.
    
    Args:
        dt: Optional datetime to convert. If None, uses current time.
        
    Returns:
        Datetime in America/Chicago timezone
    """
    chicago_tz = timezone("America/Chicago")
    
    if dt is None:
        return datetime.now(chicago_tz)
    else:
        if dt.tzinfo is None:
            # Assume UTC if no timezone info
            dt = dt.replace(tzinfo=timezone("UTC"))
        return dt.astimezone(chicago_tz)


def get_yesterday_chicago() -> str:
    """
    Get yesterday's date in Chicago timezone as YYYY-MM-DD string.
    
    Returns:
        Yesterday's date string
    """
    from datetime import timedelta
    
    chicago_now = get_chicago_time()
    yesterday = chicago_now - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


def ensure_directory_exists(path: str) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path to create
        
    Returns:
        Path object for the directory
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def safe_get_dict_value(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Safely get a value from a nested dictionary using dot notation.
    
    Args:
        data: Dictionary to search
        key_path: Key path in dot notation (e.g., "user.profile.name")
        default: Default value if key not found
        
    Returns:
        Value at key path or default
    """
    keys = key_path.split(".")
    current = data
    
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default


def validate_date_format(date_string: str) -> bool:
    """
    Validate that a string is in YYYY-MM-DD format.
    
    Args:
        date_string: Date string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    # Characters that are invalid in filenames on various systems
    invalid_chars = '<>:"/\\|?*'
    
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, "_")
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(". ")
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = "untitled"
    
    return sanitized


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length, adding suffix if truncated.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    truncate_length = max_length - len(suffix)
    if truncate_length <= 0:
        return suffix[:max_length]
    
    return text[:truncate_length] + suffix


def retry_on_exception(
    func,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying a function on specific exceptions.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Tuple of exceptions to catch and retry on
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        import time
        
        current_delay = delay
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                
                if attempt == max_retries:
                    # Last attempt failed, re-raise the exception
                    raise e
                
                logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                time.sleep(current_delay)
                current_delay *= backoff_factor
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        else:
            raise Exception("All retries failed")
    
    return wrapper


def log_execution_time(func):
    """
    Decorator to log function execution time.
    
    Args:
        func: Function to time
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        start_time = datetime.utcnow()
        logger = logging.getLogger(func.__module__)
        
        try:
            result = func(*args, **kwargs)
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"{func.__name__} completed in {duration:.2f}s")
            return result
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"{func.__name__} failed after {duration:.2f}s: {e}")
            raise
    
    return wrapper
