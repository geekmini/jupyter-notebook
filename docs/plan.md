# PDF to Markdown Conversion - Development Plan

## Current Status

The initial implementation of the PDF to Markdown Airflow DAG is complete with:

- MinIO integration for S3-compatible storage
- Parallel batch processing via Airflow dynamic task mapping
- Qwen3-VL vision model integration via OpenRouter API
- Cost tracking and metrics logging
- Automatic cleanup of temporary files

## Next Steps

### Phase 1: Auto-Trigger on New Files

**Goal**: Automatically trigger DAG when a new PDF is uploaded to MinIO

**Tasks**:
- [ ] Add S3KeySensor to watch `pdf-input` bucket for new `.pdf` files
- [ ] Configure sensor polling interval (e.g., every 30 seconds)
- [ ] Pass detected file key to downstream tasks
- [ ] Handle multiple files uploaded simultaneously

**Files to modify**:
- `dags/pdf_to_markdown.py`

---

### Phase 2: Prevent Duplicate Processing

**Goal**: Ensure the same PDF isn't processed multiple times concurrently

**Options**:
1. **Move processed files**: After processing, move PDF to `pdf-processed/` prefix
2. **Metadata tracking**: Use a database table to track processed files
3. **S3 object tags**: Tag processed files with `status=processed`

**Tasks**:
- [ ] Choose locking mechanism
- [ ] Implement file state tracking
- [ ] Add check in `get_new_pdf_key` task
- [ ] Handle edge cases (failed runs, partial processing)

---

### Phase 3: Metrics & Monitoring

**Goal**: Store processing metrics for analytics and monitoring

**Tasks**:
- [ ] Create metrics database table (PostgreSQL or separate DB)
- [ ] Store per-run metrics: pages, tokens, cost, duration, status
- [ ] Add Airflow Variables for configurable alerting thresholds
- [ ] Integrate with monitoring (Grafana, CloudWatch, etc.)

**Schema suggestion**:
```sql
CREATE TABLE pdf_conversion_metrics (
    id SERIAL PRIMARY KEY,
    dag_run_id VARCHAR(255) UNIQUE,
    pdf_filename VARCHAR(500),
    total_pages INT,
    num_batches INT,
    successful_batches INT,
    failed_batches INT,
    total_prompt_tokens INT,
    total_completion_tokens INT,
    total_cost_usd DECIMAL(10, 6),
    processing_time_seconds INT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### Phase 4: Notifications

**Goal**: Send notifications on completion or failure

**Tasks**:
- [ ] Add Slack webhook integration
- [ ] Send success notification with summary (pages, cost, output location)
- [ ] Send failure notification with error details
- [ ] Make notification channels configurable via Airflow Variables

**Files to create**:
- `src/libs/pdf_converter/notifications.py`

---

### Phase 5: API/UI for Submissions

**Goal**: Provide a simple way to submit PDFs without direct S3 access

**Options**:
1. **Simple Flask API**: Upload endpoint that writes to MinIO
2. **Airflow REST API**: Trigger DAG with file upload
3. **Streamlit UI**: Simple web interface for uploads

**Tasks**:
- [ ] Choose approach
- [ ] Implement upload endpoint/UI
- [ ] Add authentication
- [ ] Return job ID for status tracking

---

### Phase 6: Configuration Management

**Goal**: Make the DAG more configurable without code changes

**Tasks**:
- [ ] Move constants to Airflow Variables:
  - `BATCH_SIZE`
  - `MAX_ACTIVE_BATCHES`
  - `DPI`
  - `MODEL`
- [ ] Add per-run configuration override via DAG conf
- [ ] Document all configuration options

---

### Phase 7: Testing

**Goal**: Add comprehensive tests for reliability

**Tasks**:
- [ ] Unit tests for `pdf_converter` library functions
- [ ] Integration tests with mock S3 (moto)
- [ ] DAG validation tests
- [ ] End-to-end test with sample PDF

**Files to create**:
- `tests/test_pdf_converter/`
- `tests/test_dags/`

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         MinIO                                    │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │ pdf-input   │  │ markdown-output │  │ temp                │  │
│  │ (source)    │  │ (results)       │  │ (intermediate PNGs) │  │
│  └──────┬──────┘  └────────▲────────┘  └──────────▲──────────┘  │
└─────────┼──────────────────┼─────────────────────┼──────────────┘
          │                  │                     │
          ▼                  │                     │
┌─────────────────────────────────────────────────────────────────┐
│                      Airflow DAG                                 │
│                                                                  │
│  ┌──────────────┐    ┌───────────────────┐                      │
│  │ S3KeySensor  │───▶│ convert_to_images │──────────────────┐   │
│  │ (future)     │    └─────────┬─────────┘                  │   │
│  └──────────────┘              │                            │   │
│                                ▼                            │   │
│                    ┌───────────────────────┐                │   │
│                    │ create_batch_configs  │                │   │
│                    └───────────┬───────────┘                │   │
│                                │                            │   │
│         ┌──────────────────────┼──────────────────────┐     │   │
│         ▼                      ▼                      ▼     │   │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐│   │
│  │ process_    │       │ process_    │       │ process_    ││   │
│  │ batch_1     │       │ batch_2     │  ...  │ batch_N     ││   │
│  └──────┬──────┘       └──────┬──────┘       └──────┬──────┘│   │
│         │                     │                     │       │   │
│         └─────────────────────┼─────────────────────┘       │   │
│                               ▼                             │   │
│                    ┌───────────────────┐                    │   │
│                    │ aggregate_results │                    │   │
│                    └─────────┬─────────┘                    │   │
│                              │                              │   │
│                              ▼                              │   │
│                    ┌───────────────────┐                    │   │
│                    │ cleanup_temp_files│◀───────────────────┘   │
│                    └───────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌───────────────────┐
                    │   OpenRouter API  │
                    │   (Qwen3-VL)      │
                    └───────────────────┘
```

## Quick Reference

### Start Services
```bash
just airflow-up
```

### Access UIs
- **Airflow**: http://localhost:8080 (airflow/airflow)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

### Trigger DAG Manually
```bash
# Via Airflow CLI
just airflow-cli dags trigger pdf_to_markdown --conf '{"pdf_key": "example.pdf"}'

# Via Airflow UI
# Go to DAGs > pdf_to_markdown > Trigger DAG w/ config
```

### View Logs
```bash
just airflow-logs
```

### Stop Services
```bash
just airflow-down
```
