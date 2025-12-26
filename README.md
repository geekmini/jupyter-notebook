# Jupyter Notebook

## Prerequisites

```sh
brew install claude-code
```

## Setup

Run the setup command in Claude Code:

```sh
claude -p /setup
```

This will install all required tools (Homebrew, Python, uv, just, OrbStack), create `.env` from `.env.example`, sync dependencies, and setup git hooks.

## Local URLs

| Service       | URL                   | Credentials               |
| ------------- | --------------------- | ------------------------- |
| Airflow       | http://localhost:8080 | `airflow` / `airflow`     |
| MinIO Console | http://localhost:9003 | `minioadmin` / `minioadmin` |
| MinIO API     | http://localhost:9002 | -                         |
