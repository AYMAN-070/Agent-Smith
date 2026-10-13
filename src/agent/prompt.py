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
                {"role": "user", "parts": [{"text": self.task_definition}]}
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
