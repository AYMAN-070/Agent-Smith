from src.models import MBPPTaskInput


class Prompt:
    def __init__(self, task: MBPPTaskInput) -> None:
        self.task = task
        self.extract_task()
        self.prompt_creation()

    def extract_task(self) -> None:
        self.task_definition = self.task.task_definition
        self.function = self.task.function_definition
        self.test_list = self.task.test_list

    def prompt_creation(self) -> None:
        self.payload = {
            # System instructions to define
            # the model's persona, constraints, and behavior
            "system_instruction": {
                "parts": [
                    {
                        "text": "You are a professional Python developer."
                        "Answer concisely and only"
                        " in Python code when applicable."
                    }
                ]
            },
            # User prompt / conversation history
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                f"{self.task_definition}\n\n"
                                f"You MUST implement this exact function signature:\n"
                                f"{self.function}"
                            )
                        }
                    ],
                }
            ],
            # Generation parameters to tune the output
            "generationConfig": {
                # Lower values result in more deterministic and focused
                # responses
                "temperature": 0.2,
                "maxOutputTokens": 1000,  # Maximum number of tokens
                # the model can generate
                # Nucleus sampling: selects tokens whose cumulative probability
                # reaches P
                "topP": 0.95,
                # Top-K sampling: limits selection to the top K most probable
                # tokens
                "topK": 40,
            },
        }

    # def model_prompt(self, llm_text: str):
    # def trace_prompt(self):
