"""LLM request handling and response parsing for Agent Smith."""

import time
from typing import Any

from src.agent.prompt import PromptBuilder, SWEPromptBuilder
from src.llm.parser import ResponseParser
from src.llm.provider import Provider


class LlmResponse:
    """Wraps and parses LLM API responses including token usage and code."""

    def __init__(
        self, data: dict[str, Any], request_time_ms: float, retries: int
    ) -> None:
        """Initialize response object with API payload, latency, and retry count."""
        self.raw_data = data
        self.request_time_ms = request_time_ms
        self.model_name: str = data.get("model", "")
        self.retries = retries

        choices = data.get("choices") or [{}]
        message = choices[0].get("message", {}) if choices else {}
        raw_content = message.get("content")
        self.llm_output: str = str(raw_content) if raw_content is not None else ""
        parser = ResponseParser(self.llm_output)
        self.code: str = parser.code
        self.is_malformed: bool = parser.is_malformed
        self.malformed_reason: str = parser.malformed_reason
        self.url: str = data.get("url", "")

        usage = data.get("usage", {})
        self.input_tokens: int = usage.get("prompt_tokens", 0)
        self.output_tokens: int = usage.get("completion_tokens", 0)

    def parse(self, llm_text: str) -> str:
        """Parse raw LLM output and extract executable Python code."""
        return ResponseParser.parse(llm_text)


class LlmRequest:
    """Manages LLM API requests and code generation for agent prompts."""

    def __init__(
        self, model: str | None = None, provider: str | None = None
    ) -> None:
        """Initialize LLM request handler with optional model and provider overrides."""
        self.provider = Provider(model, provider)

    def generate_code(
        self, prompt: PromptBuilder | SWEPromptBuilder
    ) -> LlmResponse:
        """Send prompt payload to the provider and return parsed LlmResponse."""
        start_time = time.time()
        data, retries = self.provider.send_request(prompt.payload)
        request_time_ms = (time.time() - start_time) * 1000.0
        return LlmResponse(data, request_time_ms, retries)
