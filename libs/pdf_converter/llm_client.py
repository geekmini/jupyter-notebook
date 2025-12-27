"""LLM client for OpenRouter API interactions."""

import base64
import logging
import os

import requests

from .models import LLMResponse


logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMClient:
    """Client for interacting with LLM models via OpenRouter."""

    def __init__(self, api_key: str | None = None):
        """Initialize LLM client.

        Args:
            api_key: OpenRouter API key. Defaults to OPENROUTER_API_KEY env var.

        Raises:
            ValueError: If API key is not provided.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

    def call_text(
        self,
        model: str,
        prompt: str,
        content: str,
        max_tokens: int = 16000,
        timeout: int = 300,
    ) -> LLMResponse:
        """Call LLM with text content.

        Args:
            model: OpenRouter model identifier (e.g., 'anthropic/claude-3-haiku')
            prompt: System/instruction prompt
            content: User content to process
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds

        Returns:
            LLMResponse with generated content and usage stats
        """
        messages = [
            {"role": "user", "content": f"{prompt}\n\n{content}"},
        ]

        return self._call_api(model, messages, max_tokens, timeout)

    def call_with_images(
        self,
        model: str,
        prompt: str,
        image_data_list: list[bytes],
        max_tokens: int = 16000,
        timeout: int = 300,
    ) -> LLMResponse:
        """Call LLM with images (vision model).

        Args:
            model: OpenRouter model identifier (e.g., 'qwen/qwen3-vl-235b-a22b-instruct')
            prompt: Instruction prompt
            image_data_list: List of PNG image bytes
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds

        Returns:
            LLMResponse with generated content and usage stats
        """
        # Build content array with all images
        content = []
        for img_data in image_data_list:
            img_b64 = base64.b64encode(img_data).decode("utf-8")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                }
            )

        # Add the instruction text
        content.append({"type": "text", "text": prompt})

        messages = [{"role": "user", "content": content}]

        return self._call_api(model, messages, max_tokens, timeout)

    def _call_api(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
        timeout: int,
    ) -> LLMResponse:
        """Internal method to call OpenRouter API.

        Args:
            model: OpenRouter model identifier
            messages: Chat messages array
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds

        Returns:
            LLMResponse with generated content and usage stats

        Raises:
            requests.HTTPError: If API call fails
        """
        logger.debug(f"Calling OpenRouter API with model: {model}")

        response = requests.post(
            OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
            },
            timeout=timeout,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            logger.error(f"OpenRouter API error: {e}")
            try:
                error_body = response.json()
                logger.error(f"API error details: {error_body}")
            except Exception:
                logger.error(f"API response text: {response.text}")
            raise

        result = response.json()

        # Extract usage stats
        usage = result.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        # OpenRouter cost - check multiple possible locations
        cost_usd = usage.get("total_cost") or usage.get("cost") or result.get("total_cost") or 0.0

        # Extract content with defensive parsing
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected API response format: {result}")
            raise ValueError(f"Invalid API response structure: {e}") from e

        return LLMResponse(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=float(cost_usd),
            raw_response=result,
        )
