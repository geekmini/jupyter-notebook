"""Generate batch configurations for parallel processing."""

import logging
from pathlib import Path

from .models import BatchConfig
from .prompts import Language


logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 10


def generate_batch_configs(
    image_s3_keys: list[str],
    pdf_filename: str,
    dag_run_id: str,
    language: Language = Language.CHINESE,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[dict]:
    """Generate batch configurations for parallel processing.

    Args:
        image_s3_keys: List of S3 keys for PNG images (in page order)
        pdf_filename: Original PDF filename
        dag_run_id: Unique identifier for this DAG run
        language: Target output language (default: Chinese)
        batch_size: Number of pages per batch

    Returns:
        List of BatchConfig dictionaries for XCom serialization
    """
    total_pages = len(image_s3_keys)
    num_batches = (total_pages + batch_size - 1) // batch_size

    logger.info(
        f"Generating {num_batches} batch configs for {total_pages} pages "
        f"(batch_size={batch_size}, language={language.value})"
    )

    batch_configs: list[dict] = []

    for batch_id in range(num_batches):
        start_idx = batch_id * batch_size
        end_idx = min(start_idx + batch_size, total_pages)

        config = BatchConfig(
            batch_id=batch_id,
            start_page=start_idx + 1,  # 1-indexed for human readability
            end_page=end_idx,
            image_s3_keys=image_s3_keys[start_idx:end_idx],
            pdf_filename=Path(pdf_filename).stem,
            dag_run_id=dag_run_id,
            language=language,
        )

        batch_configs.append(config.to_dict())

    logger.info(f"Generated {len(batch_configs)} batch configurations")
    return batch_configs
