"""PDF to PNG image conversion."""

import logging
from pathlib import Path

import pymupdf  # type: ignore[import-untyped]

from .s3_client import S3Client


logger = logging.getLogger(__name__)

# Constants
DEFAULT_DPI = 150
TEMP_BUCKET = "temp"


def pdf_to_images(
    pdf_s3_key: str,
    dag_run_id: str,
    s3_client: S3Client,
    input_bucket: str = "pdf-input",
    dpi: int = DEFAULT_DPI,
) -> list[str]:
    """Convert PDF to PNG images and upload to S3 temp bucket.

    Images are cached by PDF filename - if images already exist in the temp bucket,
    they are reused without re-conversion.

    Args:
        pdf_s3_key: S3 key of PDF file in input bucket
        dag_run_id: Unique identifier for this DAG run (used for local temp files only)
        s3_client: S3 client instance
        input_bucket: Name of input bucket containing PDF
        dpi: Resolution for rendering (150 = 2x scale)

    Returns:
        List of S3 keys for uploaded PNG images in temp bucket
    """
    pdf_filename = Path(pdf_s3_key).name
    pdf_stem = Path(pdf_filename).stem

    # Check if cached images exist (cache key is pdf_stem, not dag_run_id)
    cache_prefix = f"{pdf_stem}/"
    cached_keys = s3_client.list_objects(TEMP_BUCKET, cache_prefix)
    cached_images = sorted([k for k in cached_keys if k.endswith(".png")])

    if cached_images:
        logger.info(f"Found {len(cached_images)} cached images for '{pdf_stem}', skipping conversion")
        return cached_images

    # No cache - download PDF and convert
    logger.info(f"No cached images found for '{pdf_stem}', converting PDF to images")
    temp_pdf_path = Path(f"/tmp/{dag_run_id}/{pdf_filename}")
    s3_client.download_file(input_bucket, pdf_s3_key, temp_pdf_path)

    # Open PDF with context manager to ensure cleanup on exception
    doc = pymupdf.open(str(temp_pdf_path))
    try:
        total_pages = len(doc)
        logger.info(f"Converting {total_pages} pages to images at {dpi} DPI")

        # Calculate zoom factor for desired DPI (72 is PDF base DPI)
        zoom = dpi / 72
        mat = pymupdf.Matrix(zoom, zoom)

        image_s3_keys: list[str] = []

        for page_num in range(total_pages):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=mat)

            # Get PNG bytes
            png_bytes = pix.tobytes("png")

            # Upload directly to S3 temp bucket (cache key is pdf_stem, not dag_run_id)
            image_key = f"{pdf_stem}/page_{page_num + 1:04d}.png"
            s3_client.upload_bytes(png_bytes, TEMP_BUCKET, image_key)
            image_s3_keys.append(image_key)

            if (page_num + 1) % 10 == 0 or page_num == total_pages - 1:
                logger.info(f"Converted page {page_num + 1}/{total_pages}")
    finally:
        doc.close()

    # Clean up temp PDF file and parent directory
    try:
        temp_pdf_path.unlink()
        temp_pdf_path.parent.rmdir()  # Remove empty parent directory
    except FileNotFoundError:
        pass  # Already cleaned up
    except OSError as e:
        logger.warning(f"Failed to cleanup temp files: {e}")

    logger.info(f"Done! {len(image_s3_keys)} images uploaded to s3://{TEMP_BUCKET}/{pdf_stem}/")
    return image_s3_keys
