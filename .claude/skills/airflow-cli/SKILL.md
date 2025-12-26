---
name: airflow-cli
description: This skill should be used when interacting with local Airflow instance via CLI. Triggers on "check DAG status", "list DAG runs", "view task logs", "trigger DAG", "get task states", "list pools", "list variables", or any Airflow CLI operations.
---

# Airflow CLI

Two ways to run commands:
```sh
# Via just (simpler)
just airflow-cli <command>

# Via docker directly (use for complex args with spaces/quotes)
docker compose exec -T airflow-apiserver airflow <command>
```

## DAG Runs

```sh
# List all runs for a DAG (dag_id is POSITIONAL, not --dag-id)
just airflow-cli dags list-runs pdf_to_markdown -o json

# Get DAG run state
just airflow-cli dags state pdf_to_markdown "2025-12-26T12:45:26+00:00"

# Trigger a DAG
just airflow-cli dags trigger pdf_to_markdown --conf '{"pdf_key": "file.pdf"}'
```

## Task Operations

```sh
# List tasks in a DAG
just airflow-cli tasks list pdf_to_markdown

# Get task states for a specific run (shows map_index for dynamic tasks)
just airflow-cli tasks states-for-dag-run pdf_to_markdown "manual__2025-12-26T12:45:26+00:00"

# View task logs
just airflow-cli tasks logs pdf_to_markdown get_new_pdf_key "2025-12-26T12:45:26+00:00"
```

## DAG Management

```sh
# List all DAGs
just airflow-cli dags list -o json

# Pause/unpause
just airflow-cli dags pause pdf_to_markdown
just airflow-cli dags unpause pdf_to_markdown
```

## Pools

```sh
# List pools
just airflow-cli pools list

# Create pool (use docker exec for descriptions with spaces)
docker compose exec -T airflow-apiserver airflow pools set my_pool 5 "My description"
```

## Variables

```sh
just airflow-cli variables list -o json
just airflow-cli variables set key value
just airflow-cli variables get key
```

## Gotchas

- **Positional args**: `dag_id` is positional (not `--dag-id`)
- **Quoting issues**: `just airflow-cli` struggles with spaces in args - use `docker compose exec` directly
- **Dynamic tasks**: `states-for-dag-run` shows `map_index` column for mapped tasks
- **Output**: Add `-o json` for JSON, `-o table` for table (default)

## Project-Specific

**DAG:** `pdf_to_markdown` - Convert PDF to Markdown via Qwen3-VL

**Auto-configured pools** (via `airflow-setup` service):
- `openrouter_api_pool` (5 slots)

**Quick commands:**
```sh
# Check DAG status
just airflow-cli dags list-runs pdf_to_markdown -o json

# Check task states
just airflow-cli tasks states-for-dag-run pdf_to_markdown "manual__<date>"

# Trigger with test config
just airflow-cli dags trigger pdf_to_markdown --conf '{"pdf_key": "test.pdf", "max_pages": 3}'
```
