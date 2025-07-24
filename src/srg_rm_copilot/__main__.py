"""
Main entry point for the SRG RM Copilot CLI.

This module allows the package to be executed as a module:
    python -m srg_rm_copilot
"""

from .cli import app

if __name__ == "__main__":
    app()
