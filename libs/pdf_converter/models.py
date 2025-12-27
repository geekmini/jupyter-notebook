"""Data models for PDF to Markdown conversion."""

from dataclasses import dataclass, field
from typing import Any

from .prompts import Language


@dataclass
class ConversionResult:
    """Result of a single batch conversion to markdown."""

    markdown: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    raw_response: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class BatchConfig:
    """Configuration for a single batch to process."""

    batch_id: int
    start_page: int
    end_page: int
    image_s3_keys: list[str]
    pdf_filename: str
    dag_run_id: str
    language: Language = Language.CHINESE

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for XCom serialization."""
        return {
            "batch_id": self.batch_id,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "image_s3_keys": self.image_s3_keys,
            "pdf_filename": self.pdf_filename,
            "dag_run_id": self.dag_run_id,
            "language": self.language.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchConfig":
        """Create from dictionary (XCom deserialization)."""
        return cls(
            batch_id=data["batch_id"],
            start_page=data["start_page"],
            end_page=data["end_page"],
            image_s3_keys=data["image_s3_keys"],
            pdf_filename=data["pdf_filename"],
            dag_run_id=data["dag_run_id"],
            language=Language(data.get("language", "zh")),
        )


@dataclass
class BatchResult:
    """Result of processing a single batch."""

    batch_id: int
    start_page: int
    end_page: int
    markdown_s3_key: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    success: bool
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for XCom serialization."""
        return {
            "batch_id": self.batch_id,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "markdown_s3_key": self.markdown_s3_key,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": self.cost_usd,
            "success": self.success,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchResult":
        """Create from dictionary (XCom deserialization)."""
        return cls(
            batch_id=data["batch_id"],
            start_page=data["start_page"],
            end_page=data["end_page"],
            markdown_s3_key=data["markdown_s3_key"],
            prompt_tokens=data["prompt_tokens"],
            completion_tokens=data["completion_tokens"],
            cost_usd=data["cost_usd"],
            success=data["success"],
            error_message=data.get("error_message"),
        )


@dataclass
class DAGRunMetrics:
    """Aggregated metrics for entire DAG run."""

    dag_run_id: str
    pdf_filename: str
    total_pages: int
    num_batches: int
    successful_batches: int
    failed_batches: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float
    markdown_s3_keys: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "dag_run_id": self.dag_run_id,
            "pdf_filename": self.pdf_filename,
            "total_pages": self.total_pages,
            "num_batches": self.num_batches,
            "successful_batches": self.successful_batches,
            "failed_batches": self.failed_batches,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_cost_usd": self.total_cost_usd,
            "cost_per_page": self.total_cost_usd / self.total_pages if self.total_pages > 0 else 0,
            "markdown_s3_keys": self.markdown_s3_keys,
        }


@dataclass
class LLMResponse:
    """Generic response from LLM API call."""

    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    raw_response: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class FormattingConfig:
    """Configuration for formatting a single markdown file."""

    markdown_s3_key: str
    output_bucket: str
    language: Language = Language.CHINESE

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for XCom serialization."""
        return {
            "markdown_s3_key": self.markdown_s3_key,
            "output_bucket": self.output_bucket,
            "language": self.language.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FormattingConfig":
        """Create from dictionary (XCom deserialization)."""
        return cls(
            markdown_s3_key=data["markdown_s3_key"],
            output_bucket=data["output_bucket"],
            language=Language(data.get("language", "zh")),
        )


@dataclass
class FormattingResult:
    """Result of formatting a single markdown file."""

    markdown_s3_key: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    success: bool
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for XCom serialization."""
        return {
            "markdown_s3_key": self.markdown_s3_key,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": self.cost_usd,
            "success": self.success,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FormattingResult":
        """Create from dictionary (XCom deserialization)."""
        return cls(
            markdown_s3_key=data["markdown_s3_key"],
            prompt_tokens=data["prompt_tokens"],
            completion_tokens=data["completion_tokens"],
            cost_usd=data["cost_usd"],
            success=data["success"],
            error_message=data.get("error_message"),
        )
