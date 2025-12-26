# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Claude Commands

- `/setup` - Initialize the project (creates .env from .env.example, installs dependencies, sets up git hooks)

## Commands

All commands use `just` (command runner) + `uv` (Python package manager):

```sh
just              # List all available commands
just init         # Setup project (sync deps + git hooks)
just sync         # Install all dependencies
just lint         # Run ruff linter
just lint-fix     # Auto-fix lint issues
just fmt          # Format code with ruff
just check        # Run lint + format check (pre-commit)
just test         # Run pytest
just run <cmd>    # Run any Python command via uv
```

### Airflow

```sh
just airflow-up          # Start Airflow services
just airflow-down        # Stop Airflow services
just airflow-logs        # View service logs
just airflow-clean       # Complete cleanup (removes data)
just airflow-info        # Show Airflow info
just airflow-dags        # List DAGs
just airflow-cli <args>  # Run any Airflow CLI command
```

## Project Structure

Flat structure for simplicity - shared libraries at root level:

```
├── dags/           # Airflow DAG files
├── libs/           # Shared Python libraries (PYTHONPATH configured)
│   └── pdf_converter/
├── notebooks/      # Jupyter notebooks (spike/exploration)
├── docs/           # Project documentation
├── logs/           # Airflow task execution logs
├── plugins/        # Custom Airflow plugins
├── config/         # Airflow configuration files
├── minio-data/     # MinIO storage (gitignored)
├── pyproject.toml  # Dependencies, ruff, pyright config
└── .env            # Environment variables
```

**Why flat structure?**
- `libs/` at root (not `src/libs/`) for easy imports
- `PYTHONPATH=/opt/airflow/libs` set in docker-compose.yaml
- No `sys.path.insert()` hacks needed in DAGs

## Logging

Use Python's standard `logging` module with `__name__` - Airflow configures the handlers automatically.

```python
import logging

logger = logging.getLogger(__name__)

# Use in DAGs and libs
logger.info("Processing started")
logger.warning("Something unexpected")
logger.exception("Error occurred")  # Includes stack trace
```

**Guidelines:**
- Use `logger.info()` for normal progress messages
- Use `logger.warning()` for recoverable issues
- Use `logger.exception()` in except blocks (auto-includes traceback)
- Avoid `print()` - use logger for proper Airflow log integration

## Notebooks

Notebooks load environment from `.env` and add parent directory to `sys.path` for imports:

```python
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(".env"), override=True)
```

## DAGs

### pdf_to_markdown

Converts PDF files to Markdown using Qwen3-VL vision model with parallel batch processing.

**Trigger manually:**
```sh
# Process entire PDF
just airflow-cli dags trigger pdf_to_markdown --conf '{"pdf_key": "example.pdf"}'

# Test with limited pages (e.g., first 3 pages only)
just airflow-cli dags trigger pdf_to_markdown --conf '{"pdf_key": "example.pdf", "max_pages": 3}'
```

**MinIO Buckets:**
- `pdf-input` - Upload source PDFs here
- `markdown-output` - Converted markdown files
- `temp` - Intermediate PNG images (auto-cleaned on success)

## Airflow Pools

Pools are used for rate limiting external API calls. Pools are **auto-created** on startup via `airflow-setup` service.

**Pre-configured pools:**
- `openrouter_api_pool` (5 slots) - Limits concurrent OpenRouter API calls

**Adjust pool size via CLI:**
```sh
just airflow-cli pools set openrouter_api_pool 10 "Limit concurrent OpenRouter API calls"
```

**Or via Airflow UI:** Admin > Pools
