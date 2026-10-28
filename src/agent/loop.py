"""Agent execution loops for MBPP and SWE-bench tasks."""

import time
from pathlib import Path
from typing import Any

from src.agent.prompt import PromptBuilder, SWEPromptBuilder
from src.agent.SandboxOutputHandler import SandboxOutputHandler
from src.llm.llm import LlmRequest, LlmResponse
from src.models import (
    MBPPTaskInput,
    SolutionOutput,
    StepMetrics,
    SWEBenchTaskInput,
)
from src.sandbox.executor import SandboxExecutor


class MBPPAgentLoop:
    """Iterative agent loop for solving MBPP programming tasks."""

    def __init__(
        self,
        task: MBPPTaskInput,
        sandbox: SandboxExecutor,
        output_path: str = "solution.json",
        model_name: str | None = None,
        provider_url: str | None = None,
    ) -> None:
        """Initialize MBPP agent loop with task, sandbox, and optional model config."""
        self.task = task
        self.sandbox = sandbox
        self.output_path = output_path
        self.prompt = PromptBuilder(task, tools_manual=sandbox.tools)
        self.llm_request = LlmRequest(model_name, provider_url)

    def run(self) -> str:
        """Execute the iterative loop to solve the MBPP task."""
        start_time = time.time()
        steps_metric: list[StepMetrics] = []
        max_loop = 10
        current_loop = 0
        print("\n" + "=" * 50)
        print("🚀 START MBPP AGENT LOOP")
        print("=" * 50)

        while current_loop < max_loop:
            step = current_loop + 1
            print(f"\n--- [ITERATION {step}/{max_loop}] ---")

            print("\n🤖 [1/3] Calling LLM with current prompt/history...")
            llm_response: LlmResponse = self.llm_request.generate_code(
                self.prompt
            )
            code_for_sandbox = llm_response.code
            print("\n📥 [LLM Generated Code]:")
            print(
                code_for_sandbox
                if code_for_sandbox
                else "(No Python code detected)"
            )
            if not code_for_sandbox:
                print(
                    "⚠️  [Warning]: No code block detected. Prompting LLM to format correctly."
                )
                feedback = (
                    "Error: No executable Python code block was detected in your response.\n"
                    "You MUST wrap your Python code in ```python\n<code here>\n```.\n"
                    "If you have completed the solution, call final_answer(solution_code)."
                )
                self.prompt.add_model_response(llm_response.llm_output)
                self.prompt.add_error_feedback(
                    feedback, step=step, max_steps=max_loop
                )

                sand_answer = {
                    "status": "error",
                    "error": "No Python code found",
                    "output": "",
                }
                steps_metric.append(
                    self.record_step(llm_response, sand_answer, step)
                )
                current_loop += 1
                continue

            print("⚙️  [2/3] Executing in Sandbox...")
            sand_answer = self.sandbox.execute(code_for_sandbox)
            print("\n📤 [Sandbox Result]:", sand_answer)
            steps_metric.append(
                self.record_step(llm_response, sand_answer, step)
            )

            status = sand_answer.get("status")

            # 1. Final answer submitted by the agent
            if status == "final_answer":
                solution = sand_answer.get("answer")
                print("\n" + "=" * 50)
                print(
                    f"✅ SUCCESS: Agent called"
                    f" final_answer at iteration {step}!"
                )
                print(f"Final Solution:\n{solution}")
                print("=" * 50 + "\n")

                solution_output = self.build_solution_output(
                    status=True,
                    solution=str(solution),
                    steps=steps_metric,
                    total_time_seconds=time.time() - start_time,
                )
                Path(self.output_path).write_text(
                    solution_output.model_dump_json(indent=2), encoding="utf-8"
                )
                return str(solution)

            # 2. Code ran successfully (e.g., agent printed test results)
            elif status == "success":
                raw_observation = sand_answer.get("output", "").strip()
                observation = SandboxOutputHandler.clean_and_truncate(
                    code_for_sandbox, raw_observation
                )
                print("\n👁️  [Observation Output]:")
                print(observation if observation else "(No stdout output)")

                if not observation:
                    feedback = (
                        "Warning: You defined a function but did NOT print "
                        "any test results and did NOT call final_answer().\n"
                        "To proceed, you MUST either test your function:\n"
                        "  res = run_tests(candidate, tests)\n"
                        "  print(res)\n"
                        "Or call final_answer(solution_code)"
                        " if you are sure it works."
                    )
                elif SandboxOutputHandler.is_test_run_finished(
                    code_for_sandbox,
                    observation,
                    has_patch=True,
                    benchmark="mbpp",
                ):
                    print(
                        "🎯 MBPP tests passed! Forcing agent to submit "
                        "final_answer."
                    )
                    feedback = (
                        f"{observation}\n\n"
                        "[CRITICAL NOTICE: ALL TESTS PASSED!]\n"
                        "All assertions passed. You are done!\n"
                        "Submit your final solution immediately: "
                        "final_answer(solution_code)"
                    )
                else:
                    feedback = observation

                if getattr(llm_response, "is_malformed", False):
                    warning_note = (
                        f"[FORMATTING NOTICE]: Code block was malformed "
                        f"({llm_response.malformed_reason}), but was recovered "
                        "and executed. For subsequent steps, strictly wrap Python code "
                        "inside ```python\n<code here>\n```.\n\n"
                    )
                    feedback = warning_note + feedback

                self.prompt.add_model_response(
                    f"```python\n{code_for_sandbox}\n```"
                )
                self.prompt.add_error_feedback(
                    feedback, step=step, max_steps=max_loop
                )

            # 3. Execution error or timeout
            else:
                raw_error = (
                    sand_answer.get("error")
                    or "Execution failed without details."
                )
                if getattr(llm_response, "is_malformed", False):
                    raw_error = (
                        f"[FORMATTING NOTICE]: Code block was malformed "
                        f"({llm_response.malformed_reason}), but was recovered.\n"
                        + raw_error
                    )
                partial_out = sand_answer.get("output", "").strip()
                if partial_out:
                    raw_error += (
                        f"\n\n[Partial stdout before interruption]:\n{partial_out}"
                    )
                error_trace = SandboxOutputHandler.clean_and_truncate(
                    code_for_sandbox, raw_error
                )
                print("\n" + "!" * 50)
                print(
                    f"❌ FAILED: Error detected in sandbox at iteration {step}:"
                )
                print("-" * 50)
                print(f"{error_trace}")
                print("-" * 50)
                print(
                    "🔄 Feeding code and error trace"
                    " back to prompt for next iteration..."
                )
                print("!" * 50 + "\n")

                self.prompt.add_model_response(
                    f"```python\n{code_for_sandbox}\n```"
                )
                self.prompt.add_error_feedback(
                    f"Execution Error:\n{error_trace}",
                    step=step,
                    max_steps=max_loop,
                )

            current_loop += 1

        print("\n" + "=" * 50)
        print("⚠️ FAILURE: Max iterations reached without solving the task.")
        print("=" * 50 + "\n")
        solution_output = self.build_solution_output(
            status=False,
            solution="didnt succeed",
            steps=steps_metric,
            total_time_seconds=time.time() - start_time,
            error="Max iterations reached without solving the task.",
        )
        Path(self.output_path).write_text(
            solution_output.model_dump_json(indent=2), encoding="utf-8"
        )
        return "didnt succeed"

    def record_step(
        self, llm: LlmResponse, sandbox: dict[str, Any], step: int
    ) -> StepMetrics:
        """Record metrics and execution output for an iteration step."""
        raw_output = (
            sandbox.get("output")
            or sandbox.get("error")
            or sandbox.get("status", "")
        )
        step_metric = StepMetrics(
            step=step,
            input_tokens=llm.input_tokens,
            output_tokens=llm.output_tokens,
            request_time_ms=llm.request_time_ms,
            api_url=llm.url,
            model_name=llm.model_name,
            llm_output=llm.llm_output,
            sandbox_input=llm.code,
            sandbox_output=str(raw_output),
            retries=llm.retries,
        )
        return step_metric

    def build_solution_output(
        self,
        status: bool,
        solution: str,
        steps: list[StepMetrics],
        total_time_seconds: float,
        error: str | None = None,
    ) -> SolutionOutput:
        """Construct final SolutionOutput model from execution metrics."""
        total_iteration = len(steps)
        total_requests = len(steps) + sum(s.retries for s in steps)
        total_input_tokens = sum(s.input_tokens for s in steps)
        total_output_tokens = sum(s.output_tokens for s in steps)

        solution_output = SolutionOutput(
            task_id=str(self.task.task_id),
            benchmark="mbpp",
            success=status,
            solution=solution,
            iterations=total_iteration,
            total_requests=total_requests,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_time_seconds=total_time_seconds,
            steps=steps,
            system_prompt=self.prompt.system_instruction,
            error=error,
        )
        return solution_output


class SWEAgentLoop:
    """Iterative agent loop for solving SWE-bench software engineering tasks."""

    def __init__(
        self,
        task: SWEBenchTaskInput,
        sandbox: SandboxExecutor,
        output_path: str = "solution.json",
        model_name: str | None = None,
        provider_url: str | None = None,
    ) -> None:
        """
        Initializes the loop for the Software Engineering Agent.
        """
        self.task = task
        self.sandbox = sandbox
        self.output_path = output_path
        self.issue_description = task.problem_statement
        self.prompt = SWEPromptBuilder(
            self.issue_description, tools_manual=sandbox.tools
        )
        self.llm_request = LlmRequest(model_name, provider_url)

    def run(self) -> str:
        """Execute the iterative loop to resolve the SWE-bench issue."""
        start_time = time.time()
        steps_metric: list[StepMetrics] = []
        max_loop = 30
        current_loop = 0
        tests_passed = False
        print("\n" + "=" * 50)
        print("🛠️ START SWE AGENT LOOP")
        print("=" * 50)

        while current_loop < max_loop:
            step = current_loop + 1
            print(f"\n--- [SWE ITERATION {step}/{max_loop}] ---")

            print("\n🤖 [1/3] Calling LLM with current prompt/history...")
            llm_response = self.llm_request.generate_code(self.prompt)
            code_for_sandbox = llm_response.code
            print("\n📥 [LLM Generated Code]:")
            print(
                code_for_sandbox
                if code_for_sandbox
                else "(No Python code detected)"
            )
            if not code_for_sandbox:
                print(
                    "⚠️  [Warning]: No code block detected. Prompting LLM to format correctly."
                )
                feedback = (
                    "Error: No executable Python code block detected.\n"
                    "Wrap your Python code in ```python\n<code here>\n```.\n"
                    "If you have completed the fix, call "
                    "final_answer(get_patch())."
                )
                self.prompt.add_model_response(llm_response.llm_output)
                self.prompt.add_feedback(
                    feedback, step=step, max_steps=max_loop
                )

                sand_answer = {
                    "status": "error",
                    "error": "No Python code found",
                    "output": "",
                }
                steps_metric.append(
                    self.record_step(llm_response, sand_answer, step)
                )
                current_loop += 1
                continue

            print("⚙️  [2/3] Executing in Sandbox...")
            sand_answer = self.sandbox.execute(code_for_sandbox)
            print("\n📤 [Sandbox Result]:", sand_answer)
            steps_metric.append(
                self.record_step(llm_response, sand_answer, step)
            )

            status = sand_answer.get("status")

            # 1. Final answer submitted by the agent
            if status == "final_answer":
                solution = sand_answer.get("answer", "")
                print("\n" + "=" * 50)
                print(
                    f"✅ SUCCESS: Agent called final_answer "
                    f"at iteration {step}!"
                )
                print(f"Final Solution:\n{solution}")
                print("=" * 50 + "\n")

                # Fallback: if solution is not a git patch, attempt get_patch
                patch_markers = ["diff --git", "--- a/", "+++ b/", "@@"]
                if not solution or not any(
                    m in str(solution) for m in patch_markers
                ):
                    patch_res = self.sandbox.execute("print(get_patch())")
                    if patch_res.get("status") == "success" and patch_res.get(
                        "output"
                    ):
                        candidate_patch = patch_res["output"].strip()
                        if any(m in candidate_patch for m in patch_markers):
                            solution = candidate_patch

                solution_output = self.build_solution_output(
                    status=True,
                    solution=str(solution),
                    steps=steps_metric,
                    total_time_seconds=time.time() - start_time,
                )
                Path(self.output_path).write_text(
                    solution_output.model_dump_json(indent=2), encoding="utf-8"
                )
                return str(solution)

            # 2. Code ran successfully (Agent used tools and printed results)
            elif status == "success":
                raw_observation = sand_answer.get("output", "").strip()
                observation = SandboxOutputHandler.clean_and_truncate(
                    code_for_sandbox, raw_observation
                )
                print("\n👁️  [Observation Output]:")
                print(observation if observation else "(No stdout output)")

                if "edit_file" in code_for_sandbox:
                    tests_passed = False

                has_patch = False
                if "run_tests" in code_for_sandbox:
                    patch_res = self.sandbox.execute("print(get_patch())")
                    has_patch = bool(patch_res.get("output", "").strip())

                if SandboxOutputHandler.is_test_run_finished(
                    code_for_sandbox,
                    observation,
                    has_patch=has_patch,
                    benchmark="swebench",
                ):
                    tests_passed = True
                    print(
                        "🎯 Tests passed! Forcing agent to inspect and submit."
                    )
                    feedback = (
                        SandboxOutputHandler.build_test_success_feedback(
                            observation
                        )
                    )
                elif tests_passed and "get_patch" in code_for_sandbox and (
                    "diff --git" in observation or "--- a/" in observation
                ):
                    print(
                        "🎯 Patch confirmed after tests! Forcing final_answer."
                    )
                    feedback = (
                        SandboxOutputHandler.build_patch_confirmed_feedback(
                            observation
                        )
                    )
                elif not observation:
                    feedback = (
                        "Code executed successfully with no printed output.\n"
                        "Remember to print() tool results, or verify changes "
                        "with print(get_patch())."
                    )
                else:
                    feedback = observation

                if getattr(llm_response, "is_malformed", False):
                    warning_note = (
                        f"[FORMATTING NOTICE]: Code block was malformed "
                        f"({llm_response.malformed_reason}), but was recovered "
                        "and executed. For subsequent steps, strictly wrap Python code "
                        "inside ```python\n<code here>\n```.\n\n"
                    )
                    feedback = warning_note + feedback

                self.prompt.add_model_response(
                    f"```python\n{code_for_sandbox}\n```"
                )
                self.prompt.add_feedback(
                    feedback, step=step, max_steps=max_loop
                )

            # 3. Execution error in the agent's script
            else:
                raw_error = (
                    sand_answer.get("error") or "Unknown execution error."
                )
                if getattr(llm_response, "is_malformed", False):
                    raw_error = (
                        f"[FORMATTING NOTICE]: Code block was malformed "
                        f"({llm_response.malformed_reason}), but was recovered.\n"
                        + raw_error
                    )
                partial_out = sand_answer.get("output", "").strip()
                if partial_out:
                    raw_error += (
                        f"\n\n[Partial stdout before interruption]:\n{partial_out}"
                    )
                error_trace = SandboxOutputHandler.clean_and_truncate(
                    code_for_sandbox, raw_error
                )
                print("\n" + "!" * 50)
                print(
                    f"❌ FAILED: Error detected in sandbox at iteration {step}:"
                )
                print(f"{error_trace}")
                print("!" * 50 + "\n")

                self.prompt.add_model_response(
                    f"```python\n{code_for_sandbox}\n```"
                )
                self.prompt.add_feedback(
                    f"Execution error:\n{error_trace}\n"
                    "Fix your code and try again.",
                    step=step,
                    max_steps=max_loop,
                )

            current_loop += 1

        print("\n" + "=" * 50)
        print("⚠️ FAILURE: Max iterations reached without solving the task.")
        print("=" * 50 + "\n")
        solution_output = self.build_solution_output(
            status=False,
            solution="",
            steps=steps_metric,
            total_time_seconds=time.time() - start_time,
            error="Max iterations reached without solving the task.",
        )
        Path(self.output_path).write_text(
            solution_output.model_dump_json(indent=2), encoding="utf-8"
        )
        return "FAILED"

    def record_step(
        self, llm: LlmResponse, sandbox: dict[str, Any], step: int
    ) -> StepMetrics:
        """Record metrics and execution output for an iteration step."""
        raw_output = (
            sandbox.get("output")
            or sandbox.get("error")
            or sandbox.get("status", "")
        )
        step_metric = StepMetrics(
            step=step,
            input_tokens=llm.input_tokens,
            output_tokens=llm.output_tokens,
            request_time_ms=llm.request_time_ms,
            api_url=llm.url,
            model_name=llm.model_name,
            llm_output=llm.llm_output,
            sandbox_input=llm.code,
            sandbox_output=str(raw_output),
            retries=llm.retries,
        )
        return step_metric

    def build_solution_output(
        self,
        status: bool,
        solution: str,
        steps: list[StepMetrics],
        total_time_seconds: float,
        error: str | None = None,
    ) -> SolutionOutput:
        """Construct final SolutionOutput model from execution metrics."""
        total_iteration = len(steps)
        total_requests = len(steps) + sum(s.retries for s in steps)
        total_input_tokens = sum(s.input_tokens for s in steps)
        total_output_tokens = sum(s.output_tokens for s in steps)

        solution_output = SolutionOutput(
            task_id=str(self.task.instance_id),
            benchmark="swebench",
            success=status,
            solution=solution,
            iterations=total_iteration,
            total_requests=total_requests,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_time_seconds=total_time_seconds,
            steps=steps,
            system_prompt=self.prompt.system_instruction,
            error=error,
        )
        return solution_output
