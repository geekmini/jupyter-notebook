# Load .env file
set dotenv-load
set dotenv-filename := ".env"

# List available recipes
default:
    @just --list

# Initialize project (sync deps + setup hooks)
init: sync setup-hooks

# Setup git hooks
setup-hooks:
    #!/usr/bin/env sh
    echo '#!/usr/bin/env sh\njust check' > .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo "Git hooks installed"

# Sync dependencies (install all deps including dev)
sync:
    uv sync --all-extras

# Install production dependencies only
install:
    uv sync

# Add a dependency
add *args:
    uv add {{args}}

# Add a dev dependency
add-dev *args:
    uv add --dev {{args}}

# Remove a dependency
remove *args:
    uv remove {{args}}

# Run linter
lint:
    uv run ruff check .

# Fix lint issues
lint-fix:
    uv run ruff check . --fix

# Format code
fmt:
    uv run ruff format .

# Check formatting
fmt-check:
    uv run ruff format . --check

# Run all checks (lint + format)
check: lint fmt-check

# Run tests
test:
    uv run pytest dags/tests

# Run tests in watch mode
tdd:
    uv run ptw dags/tests

# Run a Python command
run *args:
    uv run {{args}}

# Show installed packages
list:
    uv pip list

# === Airflow Commands ===

# Start Airflow services
airflow-up:
    docker compose up -d

# Stop Airflow services
airflow-down:
    docker compose down

# View Airflow logs
airflow-logs:
    docker compose logs -f

# Complete Airflow cleanup (removes data)
airflow-clean:
    docker compose down --volumes --rmi all

# Run Airflow CLI command
airflow-cli *args:
    docker compose run --rm airflow-cli airflow {{args}}

# List DAGs
airflow-dags:
    docker compose run --rm airflow-cli airflow dags list

# Airflow info
airflow-info:
    docker compose run --rm airflow-cli airflow info
