"""Airflow DAG for converting PDF files to Markdown using Qwen3-VL.

This DAG:
1. Watches MinIO pdf-input bucket for new PDF files
2. Converts PDF pages to PNG images
3. Processes images in parallel batches through Qwen3-VL API
4. Saves markdown output to markdown-output bucket
5. Cleans up temporary files

Requires:
- MinIO running with buckets: pdf-input, markdown-output, temp
- OPENROUTER_API_KEY environment variable
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from airflow.sdk import dag, task
from pdf_converter.batch_generator import generate_batch_configs
from pdf_converter.batch_processor import process_batch
from pdf_converter.image_converter import pdf_to_images
from pdf_converter.markdown_formatter import format_markdown
from pdf_converter.models import BatchResult, DAGRunMetrics, FormattingConfig, FormattingResult
from pdf_converter.prompts import Language
from pdf_converter.s3_client import S3Client


logger = logging.getLogger(__name__)

# Configuration
INPUT_BUCKET = "pdf-input"
OUTPUT_BUCKET = "markdown-output"
TEMP_BUCKET = "temp"
BATCH_SIZE = 10
MAX_ACTIVE_BATCHES = 5  # Limit parallel API calls


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=1),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(minutes=30),  # Default timeout for most tasks
}


@dag(
    dag_id="pdf_to_markdown",
    description="Convert PDF files to Markdown using Qwen3-VL vision model",
    schedule=None,  # Triggered by S3 sensor or manually
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["pdf", "markdown", "qwen3-vl", "minio"],
    max_active_runs=3,
    doc_md=__doc__,
)
def pdf_to_markdown_dag():
    """PDF to Markdown conversion DAG with parallel batch processing."""

    @task
    def get_new_pdf_key(**context) -> str:
        """Get the S3 key of the PDF to process.

        In production, this would come from the S3 sensor trigger.
        For manual runs, use dag_run.conf['pdf_key'].
        """
        # Check for manual trigger with conf
        dag_run = context.get("dag_run")
        conf = dag_run.conf if dag_run else {}
        pdf_key = conf.get("pdf_key") if conf else None

        if pdf_key:
            logger.info(f"Processing PDF from manual trigger: {pdf_key}")
            return pdf_key

        # For sensor-triggered runs, get the key from XCom or use wildcard
        # In production, integrate with S3KeySensor's found key
        s3_client = S3Client()
        pdf_keys = s3_client.list_objects(INPUT_BUCKET, "")
        pdf_keys = [k for k in pdf_keys if k.endswith(".pdf")]

        if not pdf_keys:
            raise ValueError(f"No PDF files found in s3://{INPUT_BUCKET}/")

        # Process the first unprocessed PDF
        pdf_key = pdf_keys[0]
        logger.info(f"Found PDF to process: {pdf_key}")
        return pdf_key

    @task(execution_timeout=timedelta(minutes=60))  # Large PDFs may take longer
    def convert_pdf_to_images(pdf_key: str, **context) -> list[str]:
        """Convert PDF to PNG images and upload to temp bucket.

        Supports max_pages in dag_run.conf for testing with partial PDFs.
        """
        dag_run_id = context["dag_run"].run_id
        dag_run = context.get("dag_run")
        conf = dag_run.conf if dag_run else {}
        max_pages = conf.get("max_pages") if conf else None

        s3_client = S3Client()

        logger.info(f"Converting PDF: {pdf_key} (run_id: {dag_run_id})")
        image_keys = pdf_to_images(
            pdf_s3_key=pdf_key,
            dag_run_id=dag_run_id,
            s3_client=s3_client,
            input_bucket=INPUT_BUCKET,
        )

        # Limit pages for testing if max_pages is set
        if max_pages and max_pages > 0:
            image_keys = image_keys[:max_pages]
            logger.info(f"Limited to {max_pages} pages for testing")

        return image_keys

    @task
    def create_batch_configs(image_keys: list[str], pdf_key: str, **context) -> list[dict]:
        """Generate batch configurations for parallel processing."""
        dag_run_id = context["dag_run"].run_id
        pdf_filename = Path(pdf_key).name

        # Extract target language from DAG run conf (default: Chinese)
        dag_run = context.get("dag_run")
        conf = dag_run.conf if dag_run else {}
        target_language = conf.get("target_language", "zh") if conf else "zh"

        # Convert string to Language enum with validation
        try:
            language = Language(target_language)
        except ValueError:
            logger.warning(
                f"Invalid target_language '{target_language}', falling back to Chinese. "
                f"Valid options: {[lang.value for lang in Language]}"
            )
            language = Language.CHINESE

        logger.info(f"Target language: {language.value} ({language.name})")

        configs = generate_batch_configs(
            image_s3_keys=image_keys,
            pdf_filename=pdf_filename,
            dag_run_id=dag_run_id,
            language=language,
            batch_size=BATCH_SIZE,
        )
        logger.info(f"Created {len(configs)} batch configs for {len(image_keys)} pages")
        return configs

    @task(
        retries=3,
        retry_delay=timedelta(seconds=30),
        pool="openrouter_api_pool",  # Use pool for rate limiting (create via Airflow UI/CLI)
        execution_timeout=timedelta(minutes=10),  # API calls should complete quickly
    )
    def process_batch_task(batch_config: dict) -> dict:
        """Process a single batch of images through Qwen3-VL."""
        return process_batch(batch_config)

    @task
    def create_formatting_configs(metrics: dict, **context) -> list[dict]:
        """Generate formatting configs from conversion metrics."""
        markdown_keys = metrics["markdown_s3_keys"]

        # Extract target language from DAG run conf (must match conversion stage)
        dag_run = context.get("dag_run")
        conf = dag_run.conf if dag_run else {}
        target_language = conf.get("target_language", "zh") if conf else "zh"

        try:
            language = Language(target_language)
        except ValueError:
            logger.warning(f"Invalid target_language '{target_language}' in formatting, falling back to Chinese.")
            language = Language.CHINESE

        configs = [
            FormattingConfig(
                markdown_s3_key=key,
                output_bucket=OUTPUT_BUCKET,
                language=language,
            ).to_dict()
            for key in markdown_keys
        ]
        logger.info(f"Created {len(configs)} formatting configs (language={language.value})")
        return configs

    @task(
        retries=3,
        retry_delay=timedelta(seconds=30),
        pool="openrouter_api_pool",  # Same pool as batch processing
        execution_timeout=timedelta(minutes=5),  # Formatting is faster than vision API
    )
    def format_markdown_task(formatting_config: dict) -> dict:
        """Format a single markdown file using Claude 3 Haiku."""
        return format_markdown(formatting_config)

    @task
    def aggregate_formatting_results(
        formatting_results: list[dict],
        conversion_metrics: dict,
    ) -> dict:
        """Combine conversion and formatting metrics."""
        # Parse results
        results = [FormattingResult.from_dict(r) for r in formatting_results]
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        # Calculate formatting metrics
        formatting_prompt_tokens = sum(r.prompt_tokens for r in successful)
        formatting_completion_tokens = sum(r.completion_tokens for r in successful)
        formatting_cost_usd = sum(r.cost_usd for r in successful)

        # Log formatting summary
        logger.info("=" * 60)
        logger.info("MARKDOWN FORMATTING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Files formatted: {len(successful)} ({len(failed)} failed)")
        logger.info(f"Formatting prompt tokens: {formatting_prompt_tokens:,}")
        logger.info(f"Formatting completion tokens: {formatting_completion_tokens:,}")
        logger.info(f"Formatting cost: ${formatting_cost_usd:.6f} USD")
        if failed:
            logger.warning(f"Failed files: {[r.markdown_s3_key for r in failed]}")
        logger.info("=" * 60)

        # Combine metrics
        total_cost = conversion_metrics["total_cost_usd"] + formatting_cost_usd
        logger.info(f"TOTAL PIPELINE COST: ${total_cost:.6f} USD")
        logger.info("=" * 60)

        return {
            **conversion_metrics,
            "formatting_prompt_tokens": formatting_prompt_tokens,
            "formatting_completion_tokens": formatting_completion_tokens,
            "formatting_cost_usd": formatting_cost_usd,
            "formatted_files": len(successful),
            "total_pipeline_cost_usd": total_cost,
        }

    @task
    def aggregate_results(batch_results: list[dict], pdf_key: str, image_keys: list[str], **context) -> dict:
        """Aggregate batch results and generate metrics."""
        dag_run_id = context["dag_run"].run_id
        pdf_filename = Path(pdf_key).name

        # Parse results
        results = [BatchResult.from_dict(r) for r in batch_results]

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        metrics = DAGRunMetrics(
            dag_run_id=dag_run_id,
            pdf_filename=pdf_filename,
            total_pages=len(image_keys),
            num_batches=len(results),
            successful_batches=len(successful),
            failed_batches=len(failed),
            total_prompt_tokens=sum(r.prompt_tokens for r in successful),
            total_completion_tokens=sum(r.completion_tokens for r in successful),
            total_cost_usd=sum(r.cost_usd for r in successful),
            markdown_s3_keys=[r.markdown_s3_key for r in successful],
        )

        # Log summary
        logger.info("=" * 60)
        logger.info("PDF TO MARKDOWN CONVERSION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"PDF: {metrics.pdf_filename}")
        logger.info(f"Pages processed: {metrics.total_pages}")
        logger.info(
            f"Batches: {metrics.num_batches} ({metrics.successful_batches} success, {metrics.failed_batches} failed)"
        )
        logger.info(f"Total prompt tokens: {metrics.total_prompt_tokens:,}")
        logger.info(f"Total completion tokens: {metrics.total_completion_tokens:,}")
        logger.info(f"Total cost: ${metrics.total_cost_usd:.6f} USD")
        if metrics.total_pages > 0:
            logger.info(f"Cost per page: ${metrics.total_cost_usd / metrics.total_pages:.6f} USD")
        logger.info(f"Output files: {len(metrics.markdown_s3_keys)}")
        for key in metrics.markdown_s3_keys:
            logger.info(f"  - s3://{OUTPUT_BUCKET}/{key}")
        logger.info("=" * 60)

        if failed:
            logger.warning(f"Failed batches: {[r.batch_id for r in failed]}")
            for r in failed:
                logger.warning(f"  Batch {r.batch_id}: {r.error_message}")

        return metrics.to_dict()

    # Define task flow
    pdf_key = get_new_pdf_key()
    image_keys = convert_pdf_to_images(pdf_key)
    batch_configs = create_batch_configs(image_keys, pdf_key)

    # Dynamic task mapping - process batches in parallel
    batch_results = process_batch_task.expand(batch_config=batch_configs)  # type: ignore[attr-defined]

    # Aggregate conversion results
    conversion_metrics = aggregate_results(batch_results, pdf_key, image_keys)

    # Format markdown files in parallel
    formatting_configs = create_formatting_configs(conversion_metrics)
    formatting_results = format_markdown_task.expand(formatting_config=formatting_configs)  # type: ignore[attr-defined]

    # Aggregate formatting results and combine with conversion metrics
    final_metrics = aggregate_formatting_results(formatting_results, conversion_metrics)

    # Note: Temp files (PNG images) are kept as cache for future runs
    # The final_metrics task is the last task in the DAG
    return final_metrics


# Instantiate the DAG
pdf_to_markdown_dag()
