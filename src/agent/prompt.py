"""Prompt builders for MBPP and SWE-bench agent conversations."""

from typing import Any

from src.models import MBPPTaskInput


class PromptBuilder:
    """Constructs and manages prompts for MBPP algorithmic tasks."""

    def __init__(
        self,
        task: MBPPTaskInput,
        tools_manual: str | None = None,
    ) -> None:
        """Initialize prompt builder with task data and optional tools manual."""
        self.task = task
        self.tools_manual = tools_manual
        self.extract_task()
        self.build_initial_payload()

    def extract_task(self) -> None:
        """Extract problem description, function signature, and tests from task."""
        self.task_definition = self.task.task_definition
        self.function = self.task.function_definition
        self.test_list = self.task.test_list

    def build_initial_payload(self) -> None:
        """Construct initial system and user messages payload."""
        formatted_tests = repr(self.test_list)
        manual_section = self.tools_manual or (
            "AVAILABLE TOOLS:\n"
            "1. run_tests(code: str, test_list: list[str]) -> str:\n"
            "   Runs candidate code against test assertions and returns a JSON string ('success': bool, 'output': str).\n"
            "2. final_answer(solution_code: str):\n"
            "   Call this built-in function to submit your final solution."
        )

        self.system_instruction = (
            "You are an autonomous Code Agent solving Python tasks in a sandbox.\n"
            "Output ONLY executable Python code enclosed in ```python ... ``` without any markdown or prose outside the block.\n\n"
            f"{manual_section}\n\n"
            "CRITICAL RULES:\n"
            "1. Output Observable Results: Every step must produce observable stdout.\n"
            "2. Two-Phase Discipline (Strict):\n"
            "   - Step 1 (Test): Test candidate code using `print(run_tests(candidate_code, tests))` and STOP. Wait for sandbox output.\n"
            "     Note: `run_tests` returns a JSON string (not a dict); do not index it (`res['success']`).\n"
            "   - Step 2 (Submit): In a separate step, once tests pass, submit via `final_answer(solution_code)`.\n"
            "   - NEVER call `final_answer` and `run_tests` in the same step.\n"
            "3. Test Integrity (Strict - No Cheating):\n"
            "   - NEVER modify, tamper with, or mock the test assertions or inputs (e.g. altering expected values or changing assertions to force a pass).\n"
            "   - The candidate code must genuinely pass the original tests.\n"
            "4. Implementation & Generalization:\n"
            "   - Favor standard Python string/list manipulation (split, slices) over complex regular expressions when formatting simple data.\n"
            "   - Implement complete logic handling edge cases and default returns (None, 0, False, empty values). Hidden tests are evaluated; do not overfit.\n"
            "   - For tie-breaking (equal counts/values), preserve original input order."
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
            "temperature": 0.0,
            "max_tokens": 1000,
            "top_p": 0.95,
        }

    def add_model_response(self, llm_text: str) -> None:
        """Append LLM assistant response to the conversation history."""
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": llm_text,
        }
        self.payload["messages"].append(assistant_message)

    def add_error_feedback(
        self,
        trace: str,
        step: int = 0,
        max_steps: int = 0,
    ) -> None:
        """Append sandbox output or error trace as feedback with budget."""
        type_error_hint = ""
        if "string indices must be integers" in trace or "TypeError" in trace:
            type_error_hint = (
                "\nCRITICAL NOTE: `run_tests` returns a JSON string, "
                "NOT a dict.\nDo NOT do `res['success']`! "
                "Simply `print(res)` or use `json.loads(res)`.\n"
            )

        step_header = (
            f"[STEP {step}/{max_steps}] " if step and max_steps else ""
        )
        reminder = ""
        if step and max_steps:
            remaining = max_steps - step
            if remaining <= 2:
                reminder = (
                    f"\n\n⚠️ URGENCY ALERT: Only {remaining} step(s) left! "
                    "If tests pass, submit with final_answer(solution_code)."
                )
            elif step % 5 == 0:
                reminder = (
                    f"\n\n🔔 REMINDER (Step {step}/{max_steps}):\n"
                    "1. Test candidate with run_tests(candidate, tests).\n"
                    "2. Do NOT combine run_tests and final_answer.\n"
                    "3. Submit with final_answer(solution_code) after tests pass."
                )

        feedback_text = (
            f"{step_header}OBSERVATION:\n{trace}{type_error_hint}{reminder}"
        )
        feedback: dict[str, Any] = {"role": "user", "content": feedback_text}
        self.payload["messages"].append(feedback)

    def add_feedback(
        self,
        observation: str,
        step: int = 0,
        max_steps: int = 0,
    ) -> None:
        """Alias for add_error_feedback for uniform interface."""
        self.add_error_feedback(observation, step=step, max_steps=max_steps)


class SWEPromptBuilder:
    """Constructs and manages prompts for SWE-bench bug resolution."""

    def __init__(
        self,
        bug_description: str,
        tools_manual: str | None = None,
    ) -> None:
        """Initialize SWE prompt builder with bug description and optional tools manual."""
        self.bug_description = bug_description
        self.tools_manual = tools_manual
        self.build_initial_payload()

    def build_initial_payload(self) -> None:
        """Construct initial system instruction and bug statement payload."""
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
            "You are an autonomous Software Engineer Agent solving real-world software bugs.\n"
            "You operate in a secure Python sandbox attached to the project's repository.\n\n"
            f"{manual_section}\n\n"
            "WORKFLOW GUIDELINES:\n"
            "1. LOCATE: Use `search_code` and `read_file` to locate the exact source of the bug.\n"
            "2. EDIT: Use `edit_file` to apply a minimal, surgical fix.\n"
            "3. VERIFY: Run `run_tests()` to confirm the bug is fixed and no regressions occur.\n"
            "4. SUBMIT: Check `print(get_patch())` to verify your diff, then call `final_answer(get_patch())`.\n\n"
            "CRITICAL EXECUTION RULES:\n"
            "1. All tools are callable directly as global Python functions (no import required).\n"
            "2. DO NOT use `import` (e.g. `import os`, `import sys`, or library imports) and DO NOT use `open()`.\n"
            "   Sandbox security forbids them. Interact with the repo ONLY via provided tools (`read_file`, `edit_file`, `list_files`).\n"
            "3. EXACT CODE SEARCH (CRITICAL):\n"
            "   - When using `search_code`, ALWAYS specify a specific query and a target file or subdirectory path (e.g. `search_code('class Pipeline', 'sklearn/pipeline.py')` or `search_code('def __len__', 'sklearn/compose')`).\n"
            "   - NEVER search generic short patterns (like '__len__' or 'def ') across the entire repository without a file path. It produces overwhelming output.\n"
            "4. Every script MUST produce observable output by using `print()` for tool results.\n"
            "5. When using `edit_file`, `old_str` must be exact code WITHOUT line numbers from `read_file`.\n"
            "6. Make minimal changes: do not reformat unrelated code or rewrite working functions.\n"
            "7. Use relative paths from repository root (e.g. 'src/module.py').\n"
            "8. STRICT TESTING RULES:\n"
            "   - To test and verify your fix, ALWAYS and ONLY use `print(run_tests())`.\n"
            "   - NEVER use `run_command('pytest ...')`, `unittest`, or bash to run tests. Only `run_tests()` executes the official SWE-bench evaluation benchmark.\n"
            "   - NEVER edit files in test suites (e.g. inside `tests/` or files named `test_*.py`). The evaluation strictly tests your fix against original repo tests.\n"
            "   - NEVER run `pip install` or modify the environment (this will break package dependencies).\n"
            "9. Once your fix is verified, STOP and SUBMIT: inspect with `print(get_patch())` then call `final_answer(get_patch())`.\n"
            "   Do NOT look for new bugs or attempt endless refactoring.\n"
            "10. NEVER call final_answer and exploration/edit tools in the same script.\n"
            "11. BREVITY IS MANDATORY: Output ONLY the minimal executable Python code block in ```python ... ``` without any natural language explanations, prose, or chatter.\n"
            "12. DECISIVE ACTION PRINCIPLE (CRITICAL):\n"
            "   - Do NOT re-read the same function, file, or signature repeatedly.\n"
            "   - Once you spot a missing argument, bug, or flawed condition (such as a missing parameter in a recursive call), apply `edit_file` IMMEDIATELY.\n"
            "   - Re-reading the same lines multiple times without editing is strictly forbidden.\n\n"
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
            f"BUG DESCRIPTION:\n{self.bug_description}\n\n"
            "INSTRUCTIONS:\n"
            "1. Locate the bug using `search_code` and `read_file`.\n"
            "2. DO NOT run Python snippets from the bug description with `import`.\n"
            "3. Apply your fix with `edit_file`.\n"
            "4. Verify with `run_tests()`.\n"
            "5. Submit your fix with `final_answer(get_patch())`."
        )

        self.payload: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": self.system_instruction},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.0,
            "max_tokens": 800,
            "top_p": 0.95,
        }

    def add_model_response(self, llm_text: str) -> None:
        """Append LLM assistant response to conversation history."""
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": llm_text,
        }
        self.payload["messages"].append(assistant_message)

    def add_feedback(
        self,
        observation: str,
        step: int = 0,
        max_steps: int = 0,
    ) -> None:
        """Append sandbox observation with step budget and reminders."""
        step_header = (
            f"[STEP {step}/{max_steps}] " if step and max_steps else ""
        )
        reminder = ""
        if step and max_steps:
            remaining = max_steps - step
            if remaining <= 5:
                reminder = (
                    f"\n\n⚠️ URGENCY ALERT: Only {remaining} step(s) left! "
                    "Stop exploring or modifying packages.\n"
                    "Inspect your diff with print(get_patch()) and submit "
                    "NOW with final_answer(get_patch())."
                )
            elif step % 10 == 0:
                reminder = (
                    f"\n\n🔔 RULES REMINDER (Step {step}/{max_steps}):\n"
                    "1. DO NOT run pip install or download packages.\n"
                    "2. DO NOT run scripts with `import` in the sandbox.\n"
                    "3. Use `edit_file` to apply minimal bug fixes.\n"
                    "4. To test, use `run_tests()`, NOT manual bash pytest.\n"
                    "5. Submit your fix with `final_answer(get_patch())`."
                )

        feedback_text = f"{step_header}OBSERVATION:\n{observation}{reminder}"
        feedback: dict[str, Any] = {"role": "user", "content": feedback_text}
        self.payload["messages"].append(feedback)
