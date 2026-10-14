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
        formatted_tests = repr(self.test_list)
        system_instruction = (
            "You are an autonomous Code Agent solving Python programming tasks.\n"
            "You operate in a secure execution sandbox where you write and execute Python code.\n\n"
            "AVAILABLE TOOLS:\n"
            "1. from agent_tools import run_tests, TESTS\n"
            "   - TESTS: the list of assertion strings for this task.\n"
            "   - run_tests(code: str, test_list: list[str]) -> str (JSON):\n"
            "     Runs candidate code against test assertions and returns a JSON string ('success': bool, 'output': str).\n"
            "2. final_answer(solution_code: str)\n"
            "   Call this built-in function to submit your final solution when all tests pass.\n\n"
            "CRITICAL EXECUTION RULE:\n"
            "Every response MUST produce observable output in the sandbox. You have ONLY TWO valid response patterns:\n\n"
            "PATTERN 1 - Testing your candidate solution:\n"
            "```python\n"
            "candidate = '''\n"
            "def your_function(...):\n"
            "    ...\n"
            "'''\n"
            "from agent_tools import run_tests, TESTS\n"
            "print(run_tests(candidate, TESTS))\n"
            "```\n\n"
            "PATTERN 2 - Submitting final solution (ONLY when all tests pass):\n"
            "```python\n"
            "final_answer('''def your_function(...):\n"
            "    ...\n"
            "''')\n"
            "```\n\n"
            "NEVER define a function without either print(run_tests(...)) or final_answer(...).\n"
            "Output ONLY the python code block enclosed in ```python ... ```."
        )

        user_content = (
            f"TASK: {self.task_definition}\n\n"
            f"REQUIRED FUNCTION SIGNATURE:\n{self.function}\n\n"
            f"TEST CASES:\ntests = {formatted_tests}\n\n"
            "Start by testing your candidate implementation."
        )

        self.payload = {
            "messages": [
                {
                    "role": "system",
                    "content": system_instruction,
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            "temperature": 0.2,
            "max_tokens": 1000,
            "top_p": 0.95,
        }

    def add_model_response(self, llm_text: str) -> None:
        # In OpenAI format, previous model responses have role 'assistant' and direct 'content'
        assistant_message: dict = {"role": "assistant", "content": llm_text}
        self.payload["messages"].append(assistant_message)

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
        feedback: dict = {"role": "user", "content": feedback_text}
        self.payload["messages"].append(feedback)
