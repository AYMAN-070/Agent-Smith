from src.models import MBPPTaskInput
from typing import Any


class PromptBuilder:
    def __init__(self, task: MBPPTaskInput) -> None:
        self.task = task
        self.extract_task()
        self.messages: list[dict[str, str]] = []
        self.build_initial_payload()

    def extract_task(self) -> None:
        self.task_definition = self.task.task_definition
        self.function = self.task.function_definition
        self.test_list = self.task.test_list

    def build_initial_payload(self) -> None:
        formatted_tests = repr(self.test_list)
        self.system_instruction = (
            "You are an autonomous Code Agent"
            " solving Python programming tasks.\n"
            "You operate in a secure execution sandbox"
            " where you write and execute Python code.\n\n"
            "AVAILABLE TOOLS:\n"
            "1. from agent_tools import run_tests, TESTS\n"
            "   - TESTS: the list of assertion strings for this task.\n"
            "   - run_tests(code: str, test_list: list[str]) -> str (JSON):\n"
            "     Runs candidate code against test assertions"
            " and returns a JSON string ('success': bool, 'output': str).\n"
            "2. final_answer(solution_code: str)\n"
            "   Call this built-in function to submit"
            " your final solution when all tests pass.\n\n"
            "CRITICAL EXECUTION RULE:\n"
            "Every response MUST produce observable output in the sandbox."
            " You have ONLY TWO valid response patterns:\n\n"
            "PATTERN 1 - Testing your candidate solution:\n"
            "```python\n"
            "candidate = '''\n"
            "def your_function(...):\n"
            "    ...\n"
            "'''\n"
            "from agent_tools import run_tests, TESTS\n"
            "print(run_tests(candidate, TESTS))\n"
            "```\n\n"
            "PATTERN 2 - Submitting final solution"
            " (ONLY when all tests pass):\n"
            "```python\n"
            "final_answer('''def your_function(...):\n"
            "    ...\n"
            "''')\n"
            "```\n\n"
            "NEVER define a function without either"
            " print(run_tests(...)) or final_answer(...).\n"
            "Output ONLY the python code block enclosed in ```python ... ```."
        )

        user_content = (
            f"TASK: {self.task_definition}\n\n"
            f"REQUIRED FUNCTION SIGNATURE:\n{self.function}\n\n"
            f"TEST CASES:\ntests = {formatted_tests}\n\n"
            "Start by testing your candidate implementation."
        )

        self.payload: dict[str, Any] = {
            "messages": [
                {
                    "role": "system",
                    "content": self.system_instruction,
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
        assistant_message: dict = {"role": "assistant", "content": llm_text}
        self.payload["messages"].append(assistant_message)

    def add_error_feedback(self, trace: str) -> None:
        feedback_text = (
            f"SANDBOX FEEDBACK / OBSERVATION:\n{trace}\n\n"
            "INSTRUCTIONS FOR NEXT STEP:\n"
            "1. If tests failed, analyze the failure, correct"
            " your algorithm, and RE-TEST using:\n"
            "   ```python\n"
            "   candidate = '''\n"
            "   def your_function(...):\n"
            "       ...\n"
            "   '''\n"
            "   from agent_tools import run_tests, TESTS\n"
            "   print(run_tests(candidate, TESTS))\n"
            "   ```\n"
            "2. If all tests PASSED, call final_answer with"
            " your clean function code:\n"
            "   ```python\n"
            "   final_answer('''def your_function(...):\n"
            "       ...\n"
            "   ''')\n"
            "   ```\n"
            "IMPORTANT: Do not just define the function. You MUST"
            " either print(run_tests(...)) or call final_answer(...)."
        )
        feedback: dict = {"role": "user", "content": feedback_text}
        self.payload["messages"].append(feedback)


class SWEPromptBuilder:
    def __init__(self, issue_description: str) -> None:
        self.issue_description = issue_description
        self.build_initial_payload()

    def build_initial_payload(self) -> None:
        system_instruction = (
            "You are an autonomous Software Engineer Agent solving real-world GitHub issues.\n"
            "You operate in a secure Python sandbox attached to the project's repository.\n\n"
            "AVAILABLE TOOLS:\n"
            "1. MCP Tools (imported from agent_tools):\n"
            "   - read_file(filepath: str) -> str\n"
            "   - list_directory(path: str) -> str\n"
            "   - run_command(command: str) -> str  # Runs bash commands like 'pytest' or 'grep'\n"
            "   - edit_file(filepath: str, old_text: str, new_text: str) -> str\n"
            "2. final_answer(message: str)\n"
            "   Call this built-in function to submit your result when you are 100% sure the bug is fixed.\n\n"
            "CRITICAL EXECUTION RULE:\n"
            "To interact with the repository, you must write a Python script that uses these tools, prints the result, and wait for the sandbox observation.\n\n"
            "EXAMPLE - Investigating the repository:\n"
            "```python\n"
            "from agent_tools import list_directory, read_file\n"
            "print(list_directory('.'))\n"
            "print(read_file('main.py'))\n"
            "```\n\n"
            "EXAMPLE - Submitting final solution:\n"
            "```python\n"
            "final_answer('The bug in utils.py is fixed and tests are passing.')\n"
            "```\n\n"
            "Output ONLY the python code block enclosed in ```python ... ```."
        )

        user_content = (
            f"ISSUE DESCRIPTION:\n{self.issue_description}\n\n"
            "Start by exploring the repository to find where the bug is located. Write your first Python script to list directories or read files."
        )

        self.payload = {
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
            "max_tokens": 1500,
            "top_p": 0.95,
        }

    def add_model_response(self, llm_text: str) -> None:
        assistant_message: dict = {"role": "assistant", "content": llm_text}
        self.payload["messages"].append(assistant_message)

    def add_feedback(self, trace: str) -> None:
        feedback_text = (
            f"SANDBOX FEEDBACK / OBSERVATION:\n{trace}\n\n"
            "INSTRUCTIONS FOR NEXT STEP:\n"
            "Analyze the output above. If you need more information, write another Python script using `read_file` or `run_command`.\n"
            "If you found the bug, use `edit_file` to fix it.\n"
            "If you are finished and tests pass, call `final_answer('done')`.\n"
            "Remember: Output ONLY valid python code enclosed in ```python ... ```."
        )
        feedback: dict = {"role": "user", "content": feedback_text}
        self.payload["messages"].append(feedback)
