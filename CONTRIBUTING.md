# Contributing to SRG RM Copilot

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/srg-rm-copilot.git
   cd srg-rm-copilot
   ```

2. **Install dependencies with uv**
   ```bash
   uv sync --dev
   ```

3. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

4. **Set up environment variables**
   ```bash
   export WHEELHOUSE_API_KEY="your_key"
   export WHEELHOUSE_USER_API_KEY="your_user_key"
   export OPENAI_API_KEY="your_openai_key"
   ```

## Code Quality Standards

### Formatting and Linting

We use `ruff` for linting and `black` for formatting:

```bash
# Check linting
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Format code
black .

# Check formatting without changing files
black --check .
