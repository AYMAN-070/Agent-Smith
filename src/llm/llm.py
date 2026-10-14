from src.agent.parser import CodeParser
from src.agent.prompt import PromptBuilder
from src.llm.provider import Provider
from src.models import StepMetrics


class Llm_request:
    def __init__(self) -> None:
        self.provider = Provider()

    def generate_code(self, prompt: PromptBuilder) -> StepMetrics:

        data = self.provider.send_request(prompt.payload).json()
        return StepMetrics(**data)
