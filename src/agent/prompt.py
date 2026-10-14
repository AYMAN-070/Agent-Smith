from src.models import MBPPTaskInput


class PromptBuilder:
    def __init__(self, task: MBPPTaskInput) -> None:
        self.task = task
        self.extract_task()
        self.build_initial_payload()

    def extract_task(self) -> None:
        self.task_definition = self.task.task_definition
        self.function = self.task.function_definition
        self.test_list = self.task.test_list

    def build_initial_payload(self) -> None:
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
                                f"You MUST implement this exact "
                                "function signature:\n"
                                f"{self.function}\n\n"
                                f"Here a assert exemple\n"
                                f"{'\n'.join(self.test_list)}"
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

    def add_model_response(self, llm_text: str) -> None:
        llm_answer: dict = {"role": "model", "parts": [{"text": llm_text}]}
        self.payload["contents"].append(llm_answer)

    def add_error_feedback(self, trace: str) -> None:
        feedback_text = (
            "The previous code failed when executed in the sandbox.\n\n"
            f"Error details / traceback:\n{trace}\n\n"
            "Instructions to fix:\n"
            "1. Carefully analyze why the error occurred.\n"
            f"2. Keep the exact function signature: {self.function}\n"
            "3. Make sure all edge cases and assertions are satisfied.\n"
            "4. Return ONLY the complete, corrected Python function enclosed in a ```python ... ``` block."
        )
        feedback: dict = {"role": "user", "parts": [{"text": feedback_text}]}
        self.payload["contents"].append(feedback)
