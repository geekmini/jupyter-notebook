# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

## Project Structure

- `src/notebooks/` - Jupyter notebooks
- `src/libs/` - Shared Python libraries for notebooks
- `pyproject.toml` - All config: dependencies, ruff, pyright
- `.env.local` - Local environment variables (loaded via python-dotenv)

## Notebooks

Notebooks load environment from `.env.local` and add parent directory to `sys.path` for imports:

```python
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(".env.local"), override=True)
```
