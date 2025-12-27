"""Markdown formatting using LLM for cleanup and structure improvement."""

import logging

from .llm_client import LLMClient
from .models import FormattingConfig, FormattingResult
from .s3_client import S3Client


logger = logging.getLogger(__name__)

# Default model for formatting (Claude 3 Haiku - fast and cheap for text tasks)
DEFAULT_FORMATTING_MODEL = "anthropic/claude-3-haiku"

FORMATTING_PROMPT = """Clean up and fix the structure of this markdown document.

Tasks:
1. Fix heading hierarchy (ensure proper H1 → H2 → H3 nesting)
2. Remove artifacts (page numbers, headers/footers if duplicated)
3. Normalize formatting (consistent list styles, table alignment)
4. Remove excessive blank lines while preserving readability
5. Fix any broken tables or lists

Preserve all content - do not summarize or omit text.
Output only the formatted markdown, no explanations."""


def format_markdown(
    formatting_config: dict,
    s3_client: S3Client | None = None,
    llm_client: LLMClient | None = None,
    model: str = DEFAULT_FORMATTING_MODEL,
) -> dict:
    """Format a single markdown file using LLM.

    This function is designed to be called by Airflow's dynamic task mapping.

    Args:
        formatting_config: FormattingConfig dictionary from XCom
        s3_client: Optional S3 client (creates one if not provided)
        llm_client: Optional LLM client (creates one if not provided)
        model: Model identifier for formatting

    Returns:
        FormattingResult dictionary for XCom serialization
    """
    config = FormattingConfig.from_dict(formatting_config)
    logger.info(f"Formatting markdown file: {config.markdown_s3_key}")

    # Initialize clients
    if s3_client is None:
        s3_client = S3Client()

    if llm_client is None:
        llm_client = LLMClient()

    try:
        # Download markdown from S3
        markdown_bytes = s3_client.download_bytes(config.output_bucket, config.markdown_s3_key)
        original_markdown = markdown_bytes.decode("utf-8")

        logger.info(f"Downloaded {len(original_markdown)} characters from {config.markdown_s3_key}")

        # Call LLM for formatting
        llm_response = llm_client.call_text(
            model=model,
            prompt=FORMATTING_PROMPT,
            content=original_markdown,
            max_tokens=16000,
            timeout=300,
        )

        formatted_markdown = llm_response.content

        # Upload formatted markdown back to S3 (overwrite original)
        s3_client.upload_text(formatted_markdown, config.output_bucket, config.markdown_s3_key)

        logger.info(
            f"Formatted {config.markdown_s3_key}: {llm_response.prompt_tokens} prompt tokens, "
            f"{llm_response.completion_tokens} completion tokens, ${llm_response.cost_usd:.6f}"
        )

        result = FormattingResult(
            markdown_s3_key=config.markdown_s3_key,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            cost_usd=llm_response.cost_usd,
            success=True,
        )

    except Exception as e:
        # Log error and re-raise for Airflow retry mechanism
        logger.exception(f"Failed to format {config.markdown_s3_key}: {e}")
        raise

    return result.to_dict()
