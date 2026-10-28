"""LLM request dispatcher and response parser."""

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

        self.llm_output: str = data["choices"][0]["message"]["content"]
        self.code: str = self.parse(self.llm_output)
        self.url = data["url"]

        usage = data.get("usage", {})
        self.input_tokens: int = usage.get("prompt_tokens", 0)
        self.output_tokens: int = usage.get("completion_tokens", 0)

    def parse(self, llm_text: str) -> str:
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
