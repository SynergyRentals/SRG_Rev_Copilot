"""
SRG RM Copilot

Production-ready Python package + CLI + ETL for Wheelhouse data with AI-powered development automation.
"""

__version__ = "0.1.0"
__author__ = "SRG Team"
__email__ = "team@srg.com"

from .config import Config
from .wheelhouse import WheelhouseClient
from .etl import ETLProcessor
from .llm import LLMClient

__all__ = [
    "Config",
    "WheelhouseClient", 
    "ETLProcessor",
    "LLMClient",
]
