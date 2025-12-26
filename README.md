# Jupyter Notebook

## Prerequisites

- macOS with [Homebrew](https://brew.sh/)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) - AI-powered CLI

```sh
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Claude Code
brew install claude-code
```

## Setup

Run the setup command in Claude Code:

```sh
claude -p /setup
```

This will install all required tools (Python, uv, just, OrbStack), create `.env` from `.env.example`, sync dependencies, and setup git hooks.

## Local URLs

| Service | URL                   | Credentials         |
| ------- | --------------------- | ------------------- |
| Airflow | http://localhost:8080 | `airflow` `airflow` |
