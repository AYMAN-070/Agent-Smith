from src.models import MBPPTaskInput
from typing import Any, Optional
from src.sandbox.manual import generate_tools_manual


class PromptBuilder:
    def __init__(
        self,
        task: MBPPTaskInput,
        tools_manual: Optional[str] = None,
    ) -> None:
        self.task = task
        self.tools_manual = tools_manual
        self.extract_task()
        self.messages: list[dict[str, str]] = []
        self.build_initial_payload()

    def extract_task(self) -> None:
        self.task_definition = self.task.task_definition
        self.function = self.task.function_definition
        self.test_list = self.task.test_list

    def build_initial_payload(self) -> None:
        formatted_tests = repr(self.test_list)
        manual_section = self.tools_manual or (
            "AVAILABLE TOOLS:\n"
            "1. run_tests(code: str, test_list: list[str]) -> dict:\n"
            "   Runs candidate code against test assertions.\n"
            "2. final_answer(solution_code: str):\n"
            "   Call this built-in function to submit your final solution."
        )

        self.system_instruction = (
            "You are an autonomous Code Agent solving Python programming tasks.\n"
            "You operate in a secure execution sandbox where you write and execute Python code.\n\n"
            f"{manual_section}\n\n"
            "CRITICAL EXECUTION RULES:\n"
            "1. All tools are callable directly as global Python functions (no import required).\n"
            "2. Every response MUST produce observable output in the sandbox.\n"
            "3. TWO-PHASE DISCIPLINE (STRICT):\n"
            "   - NEVER call final_answer and run_tests in the same script.\n"
            "   - Phase 1 (Test): Call run_tests, print the result, and STOP. Wait for the sandbox observation.\n"
            "   - Phase 2 (Submit): In a subsequent step, once you observe that all tests passed, call final_answer.\n\n"
            "PATTERN 1 - Testing your candidate solution:\n"
            "```python\n"
            "candidate = '''\n"
            "def your_function(...):\n"
            "    ...\n"
            "'''\n"
            "res = run_tests(candidate, tests)\n"
            "print(res)\n"
            "```\n\n"
            "PATTERN 2 - Submitting final solution (ONLY in a separate step after tests pass):\n"
            "```python\n"
            "final_answer('''def your_function(...):\n"
            "    ...\n"
            "''')\n"
            "```\n\n"
            "NEVER combine Pattern 1 and Pattern 2 in the same step.\n"
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
            "   res = run_tests(candidate, tests)\n"
            "   print(res)\n"
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
    def __init__(
        self,
        issue_description: str,
        tools_manual: Optional[str] = None,
    ) -> None:
        self.issue_description = issue_description
        self.tools_manual = tools_manual
        self.build_initial_payload()

    def build_initial_payload(self) -> None:
        manual_section = self.tools_manual or (
            "AVAILABLE TOOLS:\n"
            "- read_file(filepath: str, start_line: int, end_line: int) -> str\n"
            "- list_files(directory: str, pattern: str) -> str\n"
            "- search_code(pattern: str, file_pattern: str) -> str\n"
            "- edit_file(filepath: str, old_str: str, new_str: str) -> str\n"
            "- run_tests() -> str\n"
            "- get_patch() -> str\n"
            "- run_command(command: str, workdir: str) -> str\n"
            "- final_answer(patch_diff: str)"
        )
        self.system_instruction = (
            "You are an autonomous Software Engineer Agent solving real-world GitHub issues.\n"
            "You operate in a secure Python sandbox attached to the project's repository.\n\n"
            f"{manual_section}\n\n"
            "CRITICAL EXECUTION RULES:\n"
            "1. To interact with the repository, you must write a Python script that uses these tools, prints the result, and wait for the sandbox observation.\n"
            "2. NEVER call final_answer and exploration/edit tools in the same script. Inspect test results first, and call final_answer in a separate step once verified.\n"
            "3. When you have fixed the bug and verified with run_tests(), retrieve and submit your patch using:\n"
            "   final_answer(get_patch())\n\n"
            "EXAMPLE - Investigating the repository:\n"
            "```python\n"
            "print(list_files('.', '*.py'))\n"
            "print(read_file('main.py', 1, 50))\n"
            "```\n\n"
            "EXAMPLE - Submitting final solution:\n"
            "```python\n"
            "final_answer(get_patch())\n"
            "```\n\n"
            "Output ONLY the python code block enclosed in ```python ... ```."
        )

        user_content = (
            f"ISSUE DESCRIPTION:\n{self.issue_description}\n\n"
            "Start by exploring the repository to find where the bug is located. Write your first Python script to search or read files."
        )

        self.payload = {
            "messages": [
                {"role": "system", "content": self.system_instruction},
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
            "Analyze the output above. If you need more information, write another Python script using `read_file`, `search_code`, or `run_command`.\n"
            "If you found the bug, use `edit_file` to fix it and verify with `run_tests()`.\n"
            "If tests pass and the fix is verified, retrieve and submit your patch with `final_answer(get_patch())`.\n"
            "Remember: Output ONLY valid python code enclosed in ```python ... ```."
        )
        feedback: dict = {"role": "user", "content": feedback_text}
        self.payload["messages"].append(feedback)
