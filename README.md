# SRG RM Copilot

A production-ready Python package and CLI for Wheelhouse data ETL with AI-powered development automation.

## Features

- **CLI Interface**: Typer-based command-line tool with rich terminal output
- **ETL Pipeline**: Extract data from Wheelhouse API, transform, and save as Parquet files
- **Health Monitoring**: Comprehensive data pipeline monitoring and reporting
- **AI Integration**: OpenAI-powered development automation through GitHub issues
- **Robust Error Handling**: Retry logic with exponential backoff for API calls
- **Configuration Management**: Environment-based configuration with validation

## Installation

### Requirements

- Python 3.12+
- uv package manager (recommended) or pip

### Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd srg-rm-copilot

# Install dependencies
uv sync --dev

# Activate the virtual environment (if needed)
source .venv/bin/activate
```

### Using pip

```bash
pip install -e .
```

## Configuration

Set the required environment variables:

```bash
export WHEELHOUSE_API_KEY='your_wheelhouse_api_key'
export WHEELHOUSE_USER_API_KEY='your_wheelhouse_user_api_key'

# Optional: For AI features
export OPENAI_API_KEY='your_openai_api_key'
```

## Usage

### CLI Commands

The package provides a command-line interface accessible via:

```bash
python -m srg_rm_copilot [COMMAND] [OPTIONS]
```

#### Available Commands

1. **ETL Process**
   ```bash
   # Process yesterday's data (default)
   python -m srg_rm_copilot etl
   
   # Process specific date
   python -m srg_rm_copilot etl --date 2025-07-01
   
   # Dry run (preview without writing files)
   python -m srg_rm_copilot etl --date 2025-07-01 --dry-run
   
   # Verbose logging
   python -m srg_rm_copilot etl --verbose
   ```

2. **Health Monitoring**
   ```bash
   # Generate health report
   python -m srg_rm_copilot health
   
   # Custom output location
   python -m srg_rm_copilot health --output /tmp/health.json
   
   # Verbose logging
   python -m srg_rm_copilot health --verbose
   ```

3. **Configuration Check**
   ```bash
   # Verify API keys and connectivity
   python -m srg_rm_copilot config-check
   ```

4. **Help and Information**
   ```bash
   # Show main help
   python -m srg_rm_copilot --help
   
   # Show command-specific help
   python -m srg_rm_copilot etl --help
   ```

## Project Structure

```
srg-rm-copilot/
├── src/srg_rm_copilot/
│   ├── __init__.py          # Package initialization and exports
│   ├── cli.py               # Command-line interface (Typer)
│   ├── config.py            # Configuration management (Pydantic)
│   ├── wheelhouse.py        # Wheelhouse API client with retry logic
│   ├── etl.py               # ETL processor for data pipeline
│   ├── health.py            # Health monitoring and reporting
│   ├── llm.py               # OpenAI integration for AI features
│   └── utils.py             # Utility functions and decorators
├── tests/                   # Test suite
│   ├── test_cli.py         # CLI testing
│   ├── test_config.py      # Configuration testing
│   ├── test_etl.py         # ETL pipeline testing
│   ├── test_health.py      # Health monitoring testing
│   ├── test_llm.py         # AI integration testing
│   └── test_wheelhouse.py  # API client testing
├── scripts/                 # Utility scripts
├── data/                    # Data storage (created at runtime)
│   ├── raw/                # Raw Parquet files organized by listing_id
│   └── health.json         # Health monitoring reports
├── .github/workflows/       # GitHub Actions
│   ├── ci.yml              # Continuous Integration
│   ├── nightly_etl.yml     # Automated nightly ETL
│   └── ai_task.yml         # AI-powered task automation
├── pyproject.toml          # Project configuration and dependencies
├── README.md               # This file
└── LICENSE                 # MIT License
```

## Data Pipeline

### ETL Process

1. **Extract**: Fetch listing data from Wheelhouse API for specified date
2. **Transform**: Process and validate data using Pandas
3. **Load**: Save as Parquet files in organized directory structure

### Data Organization

```
data/raw/
├── listing_123/
│   ├── 2025-07-01.parquet
│   ├── 2025-07-02.parquet
│   └── 2025-07-03.parquet
├── listing_456/
│   └── 2025-07-01.parquet
└── health.json
```

### Health Monitoring

The health monitor provides:
- Total file count and size statistics
- Date range analysis
- Error detection and reporting
- Storage utilization metrics
- Pipeline status assessment

## API Integration

### Wheelhouse API

- Dual authentication using API key and user API key
- Automatic retry logic with exponential backoff
- Rate limiting protection (429 error handling)
- Connection pooling for performance

### OpenAI Integration

- GPT model integration for code generation
- GitHub issue processing with `ai-task` label
- Automated pull request creation
- Error handling and fallback mechanisms

## Development

### Setup Development Environment

```bash
# Install with development dependencies
uv sync --dev

# Install pre-commit hooks
pre-commit install
```

### Code Quality

The project uses:
- **ruff**: Fast Python linting
- **black**: Code formatting
- **mypy**: Type checking
- **pre-commit**: Automated checks before commits

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/srg_rm_copilot

# Run specific test file
pytest tests/test_cli.py -v
```

### GitHub Workflows

1. **CI Pipeline** (`.github/workflows/ci.yml`)
   - Runs on pull requests and main branch pushes
   - Executes linting, type checking, and tests
   - Multi-Python version support

2. **Nightly ETL** (`.github/workflows/nightly_etl.yml`)
   - Scheduled at 02:00 America/Chicago
   - Automatically processes previous day's data
   - Stores results and health reports

3. **AI Task Automation** (`.github/workflows/ai_task.yml`)
   - Triggered by GitHub issues labeled `ai-task`
   - Uses OpenAI to generate code solutions
   - Creates pull requests with generated changes

## Configuration Options

The system supports extensive configuration through environment variables:

```python
# Required
WHEELHOUSE_API_KEY           # Wheelhouse API access key
WHEELHOUSE_USER_API_KEY      # Wheelhouse user API key

# Optional
OPENAI_API_KEY              # OpenAI API key for AI features
DATA_ROOT_PATH              # Custom data storage path (default: ./data)
BATCH_SIZE                  # API batch size (default: 100)
MAX_RETRIES                 # Retry attempts (default: 3)
RETRY_DELAY                 # Initial retry delay in seconds (default: 1.0)
BACKOFF_FACTOR              # Exponential backoff multiplier (default: 2.0)
```

## Error Handling

The system includes comprehensive error handling:

- **API Errors**: Automatic retries with exponential backoff
- **Network Issues**: Connection pooling and timeout management
- **Data Validation**: Pydantic models ensure data integrity
- **File Operations**: Graceful handling of file system errors
- **Configuration**: Clear error messages for missing requirements

## Monitoring and Observability

### Logging

- Structured logging with configurable levels
- CLI integration with verbose modes
- Separate loggers for different components

### Health Reports

The health monitoring system generates detailed JSON reports:

```json
{
  "timestamp": "2025-07-24T06:58:57.414Z",
  "status": "healthy|degraded|critical",
  "file_count": 150,
  "total_size_mb": 45.7,
  "date_range": {
    "earliest": "2025-07-01",
    "latest": "2025-07-23"
  },
  "issues": [],
  "listings": {
    "listing_123": {
      "file_count": 23,
      "size_mb": 15.2,
      "date_range": ["2025-07-01", "2025-07-23"]
    }
  }
}
```

## Security

- No hardcoded credentials in source code
- Environment variable-based configuration
- GitHub token-based authentication for workflows
- Secure API key management through environment variables

## Performance

- Connection pooling for HTTP requests
- Efficient Parquet format for data storage
- Batch processing with configurable sizes
- Lazy loading of large datasets
- Optimized pandas operations

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `pytest`
5. Run linting: `ruff check src/`
6. Format code: `black src/`
7. Commit changes: `git commit -am 'Add feature'`
8. Push to branch: `git push origin feature-name`
9. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please:
1. Check existing GitHub issues
2. Create a new issue with detailed description
3. For AI-powered assistance, label issues with `ai-task`

## Changelog

### v0.1.0 (2025-07-24)
- Initial release
- Complete CLI interface with Typer
- ETL pipeline with Wheelhouse API integration
- Health monitoring system
- OpenAI integration for AI automation
- GitHub Actions workflows
- Comprehensive test suite
- Documentation and examples