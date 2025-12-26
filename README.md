# Jupyter Notebook

## Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) - Python package manager
- [just](https://github.com/casey/just) - Command runner

```sh
brew install python@3.12 uv just
```

## Setup

```sh
just init
```

This will sync all dependencies and setup git hooks.

## Commands

```sh
just          # List all available commands
just sync     # Install all dependencies
just lint     # Run linter
just lint-fix # Auto-fix lint issues
just fmt      # Format code
just check    # Run all checks
just test     # Run tests
just run <cmd># Run any Python command
```
