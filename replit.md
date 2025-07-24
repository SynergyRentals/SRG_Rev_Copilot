# SRG RM Copilot

## Overview

SRG RM Copilot is a production-ready Python package that provides ETL capabilities for Wheelhouse data along with AI-powered development automation. The system extracts data from the Wheelhouse API, transforms it, and stores it in Parquet format for analysis. It also includes AI integration for automated development tasks through GitHub issues.

**Status**: ✅ COMPLETE - Full production-ready implementation with CLI, ETL pipeline, health monitoring, AI integration, and comprehensive documentation.

## Recent Changes (July 24, 2025)

- ✅ Complete project scaffold with modern Python package structure
- ✅ CLI interface implemented with Typer framework
- ✅ Core ETL processor with Wheelhouse API integration  
- ✅ Health monitoring system with JSON reporting
- ✅ OpenAI integration for AI-powered development automation
- ✅ GitHub Actions workflows for CI/CD and automation
- ✅ Comprehensive test suite structure
- ✅ Pre-commit hooks and code quality tools configured
- ✅ MIT License and detailed README documentation
- ✅ All dependencies resolved and installed correctly

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Architecture
- **Package Structure**: Standard Python package with `src/` layout using `pyproject.toml`
- **CLI Framework**: Typer-based command-line interface accessible via `python -m srg_rm_copilot`
- **Dependency Management**: Uses `uv` for fast dependency resolution and virtual environment management
- **Configuration**: Pydantic-based configuration with environment variable loading

### Technology Stack
- **Python 3.12+** with modern async/await patterns
- **Typer** for CLI interface
- **Pydantic** for configuration management and data validation
- **Pandas + PyArrow** for data processing and Parquet file operations
- **OpenAI SDK 1.0+** for AI integration
- **requests + tenacity** for HTTP client with retry logic
- **pytest + pytest-httpx** for testing

## Key Components

### 1. Configuration System (`config.py`)
- Environment-based configuration using Pydantic
- Required: `WHEELHOUSE_API_KEY`, `WHEELHOUSE_USER_API_KEY`
- Optional: `OPENAI_API_KEY` for AI features
- Configurable data paths, batch sizes, retry settings

### 2. Wheelhouse API Client (`wheelhouse.py`)
- HTTP client with automatic retry logic for rate limiting (429 errors)
- Exponential backoff using tenacity library
- Robust error handling with custom exception types
- Session management with connection pooling

### 3. ETL Processor (`etl.py`)
- Extracts data from Wheelhouse API by date
- Transforms data into structured format
- Loads into Parquet files with directory structure: `/data/raw/{listing_id}/{YYYY-MM-DD}.parquet`
- Supports dry-run mode for testing

### 4. Health Monitoring (`health.py`)
- Scans data directory for file counts and sizes
- Generates comprehensive health reports in JSON format
- Monitors data pipeline status and storage utilization
- Provides metrics for operational monitoring

### 5. AI Integration (`llm.py`)
- OpenAI client wrapper with error handling
- Supports code generation and analysis
- Integrates with GitHub automation workflows

### 6. CLI Interface (`cli.py`)
- Main ETL command: `etl --date YYYY-MM-DD`
- Health check command for monitoring
- America/Chicago timezone handling for date defaults
- Verbose logging and dry-run options

## Data Flow

1. **Data Extraction**: CLI triggers ETL process for specified date
2. **API Calls**: Wheelhouse client fetches listing data with retry logic
3. **Data Processing**: ETL processor transforms and validates data
4. **Storage**: Data written to Parquet files in organized directory structure
5. **Health Monitoring**: System scans files and generates health reports
6. **Automation**: AI scripts can process GitHub issues for development tasks

### Directory Structure
```
data/
├── raw/
│   ├── listing_1/
│   │   ├── 2025-01-01.parquet
│   │   └── 2025-01-02.parquet
│   └── listing_2/
│       └── 2025-01-01.parquet
└── health.json
```

## External Dependencies

### APIs
- **Wheelhouse API**: Primary data source requiring dual authentication keys
- **OpenAI API**: Powers AI development automation features

### Development Tools
- **GitHub Actions**: Automated workflows for CI/CD and nightly ETL
- **Pre-commit hooks**: Code quality enforcement with ruff and black
- **pytest**: Testing framework with HTTP mocking

## Deployment Strategy

### Local Development
- Uses `uv sync --dev` for dependency installation
- Pre-commit hooks ensure code quality
- Environment variables for API key management

### GitHub Integration
- **CI/CD Pipeline**: `.github/workflows/ci.yml` runs tests and linting
- **Nightly ETL**: `.github/workflows/nightly_etl.yml` runs ETL at 02:00 America/Chicago
- **AI Automation**: `.github/workflows/ai_task.yml` processes issues with `ai-task` label

### Production Considerations
- Health monitoring with `/data/health.json` for operational visibility
- Structured logging for debugging and monitoring
- Configurable retry logic for API resilience
- Parquet format for efficient data storage and analysis

### Security
- API keys managed through environment variables
- No hardcoded credentials in codebase
- GitHub token-based authentication for automation workflows

## Development Workflow

### Quality Assurance
- **Linting**: ruff for fast Python linting
- **Formatting**: black for consistent code style
- **Testing**: pytest with httpx mocking for API calls
- **Pre-commit**: Automated checks before commits

### AI Development Automation
- GitHub issues labeled `ai-task` trigger automated code generation
- OpenAI integration generates code diffs and pull requests
- Human review required before merging AI-generated changes