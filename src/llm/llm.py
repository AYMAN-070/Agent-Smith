import re
import time

from src.agent.prompt import PromptBuilder
from src.llm.provider import Provider


class LlmResponse:
    def __init__(self, data: dict, request_time_ms: float) -> None:

        self.raw_data = data
        self.request_time_ms = request_time_ms
        self.model_name: str = data.get("model", "")

        self.llm_output: str = data["choices"][0]["message"]["content"]

        self.code: str = self.parse(self.llm_output)

        usage = data.get("usage", {})
        self.input_tokens: int = usage.get("prompt_tokens", 0)
        self.output_tokens: int = usage.get("completion_tokens", 0)

    def parse(self, llm_text) -> str:
        pattern = r"```(?:python|py)?\s*\n(.*?)```"
        match = re.search(pattern, llm_text, re.DOTALL | re.IGNORECASE)
        if match:
            python_code = match.group(1).strip()
            return python_code
        return ""


class LlmRequest:
    def __init__(self) -> None:
        self.provider = Provider()

    def generate_code(self, prompt: PromptBuilder) -> LlmResponse:

        start_time = time.time()
        data = self.provider.send_request(prompt.payload)
        request_time_ms = (time.time() - start_time) * 1000.0
        return LlmResponse(data, request_time_ms)
