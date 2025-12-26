"""Process image batches through Qwen3-VL API."""

import base64
import logging
import os

import requests

from .models import BatchConfig, BatchResult, ConversionResult
from .s3_client import S3Client


logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "qwen/qwen3-vl-235b-a22b-instruct"
TEMP_BUCKET = "temp"
OUTPUT_BUCKET = "markdown-output"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

CONVERSION_PROMPT = """Convert these PDF pages to well-formatted markdown.
Preserve the document structure including:
- Headings and subheadings
- Paragraphs
- Bullet points and numbered lists
- Tables (use markdown table format)
- Any emphasized or bold text

Output only the markdown content, no explanations."""


def _call_qwen_api(
    image_data_list: list[bytes],
    api_key: str,
    model: str = DEFAULT_MODEL,
) -> ConversionResult:
    """Call Qwen3-VL API with images.

    Args:
        image_data_list: List of PNG image bytes
        api_key: OpenRouter API key
        model: Model identifier

    Returns:
        ConversionResult with markdown and usage stats
    """
    # Build content array with all images
    content = []
    for img_data in image_data_list:
        img_b64 = base64.b64encode(img_data).decode("utf-8")
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}})

    # Add the instruction text
    content.append({"type": "text", "text": CONVERSION_PROMPT})

    response = requests.post(
        OPENROUTER_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 16000,
        },
        timeout=300,
    )

    response.raise_for_status()
    result = response.json()

    # Extract usage stats
    usage = result.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

    # OpenRouter cost - check multiple possible locations
    cost_usd = usage.get("total_cost") or usage.get("cost") or result.get("total_cost") or 0.0

    return ConversionResult(
        markdown=result["choices"][0]["message"]["content"],
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_usd=float(cost_usd),
        raw_response=result,
    )


def process_batch(
    batch_config: dict,
    s3_client: S3Client | None = None,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Process a single batch of images through Qwen3-VL.

    This function is designed to be called by Airflow's dynamic task mapping.

    Args:
        batch_config: BatchConfig dictionary from XCom
        s3_client: Optional S3 client (creates one if not provided)
        api_key: OpenRouter API key (defaults to env var)
        model: Model identifier

    Returns:
        BatchResult dictionary for XCom serialization
    """
    config = BatchConfig.from_dict(batch_config)
    logger.info(f"Processing batch {config.batch_id}: pages {config.start_page}-{config.end_page}")

    # Initialize clients
    if s3_client is None:
        s3_client = S3Client()

    if api_key is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

    try:
        # Download images from S3
        image_data_list = []
        for image_key in config.image_s3_keys:
            image_data = s3_client.download_bytes(TEMP_BUCKET, image_key)
            image_data_list.append(image_data)

        logger.info(f"Downloaded {len(image_data_list)} images for batch {config.batch_id}")

        # Call API
        conversion_result = _call_qwen_api(image_data_list, api_key, model)

        # Upload markdown to output bucket
        markdown_key = f"{config.pdf_filename}/pages_{config.start_page:04d}-{config.end_page:04d}.md"
        s3_client.upload_text(conversion_result.markdown, OUTPUT_BUCKET, markdown_key)

        logger.info(
            f"Batch {config.batch_id} completed: {conversion_result.prompt_tokens} prompt tokens, "
            f"${conversion_result.cost_usd:.6f}"
        )

        result = BatchResult(
            batch_id=config.batch_id,
            start_page=config.start_page,
            end_page=config.end_page,
            markdown_s3_key=markdown_key,
            prompt_tokens=conversion_result.prompt_tokens,
            completion_tokens=conversion_result.completion_tokens,
            cost_usd=conversion_result.cost_usd,
            success=True,
        )

    except Exception as e:
        # Log error and re-raise for Airflow retry mechanism
        # Don't create a BatchResult here since the exception will cause retry
        logger.exception(f"Batch {config.batch_id} failed: {e}")
        raise

    return result.to_dict()
