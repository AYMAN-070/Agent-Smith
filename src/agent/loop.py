"""Agent execution loops for MBPP and SWE-bench tasks."""

import time

from src.agent.base_loop import BaseAgentLoop
from src.agent.prompt import PromptBuilder, SWEPromptBuilder
from src.agent.sandbox_output_handler import SandboxOutputHandler
from src.llm.llm import LlmResponse
from src.models import (
    MBPPTaskInput,
    StepMetrics,
    SWEBenchTaskInput,
)
from src.rules import RulesMpbb, RulesSwe
from src.sandbox.executor import SandboxExecutor


class MBPPAgentLoop(BaseAgentLoop):
    """Iterative agent loop for solving MBPP programming tasks."""

    benchmark = "mbpp"
    failure_return_value = "didnt succeed"
    failure_solution_value = "didnt succeed"

    def __init__(
        self,
        task: MBPPTaskInput,
        sandbox: SandboxExecutor,
        rules: RulesMpbb,
        output_path: str = "solution.json",
        model_name: str | None = None,
        provider_url: str | None = None,
    ) -> None:
        """Initialize MBPP agent loop with task, sandbox, and optional model config."""
        super().__init__(
            task=task,
            sandbox=sandbox,
            rules=rules,
            output_path=output_path,
            model_name=model_name,
            provider_url=provider_url,
        )
        self.prompt = PromptBuilder(task, tools_manual=sandbox.tools)

    def run(self) -> str:
        """Execute the iterative loop to solve the MBPP task."""
        start_time = time.time()
        steps_metric: list[StepMetrics] = []
        max_loop = self.rules.iterations
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
                feedback = SandboxOutputHandler.get_no_code_feedback("mbpp")
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
                limit_error = self.limit_checker(steps_metric, start_time)
                if limit_error:
                    return self._save_failure(
                        steps_metric, start_time, limit_error
                    )
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

                self._save_solution(
                    status=True,
                    solution=str(solution),
                    steps=steps_metric,
                    total_time_seconds=time.time() - start_time,
                )
                return str(solution)

            # 2. Process feedback and update prompt
            feedback = SandboxOutputHandler.get_mbpp_feedback(
                code_for_sandbox, sand_answer
            )
            self.prompt.add_model_response(
                f"```python\n{code_for_sandbox}\n```"
            )
            self.prompt.add_error_feedback(
                feedback, step=step, max_steps=max_loop
            )

            current_loop += 1

            limit_error = self.limit_checker(steps_metric, start_time)
            if limit_error:
                return self._save_failure(
                    steps_metric, start_time, limit_error
                )

        return self._save_failure(
            steps_metric,
            start_time,
            error="Iteration limit reached without solving the task.",
        )


class SWEAgentLoop(BaseAgentLoop):
    """Iterative agent loop for solving SWE-bench software engineering tasks."""

    benchmark = "swebench"
    failure_return_value = "FAILED"
    failure_solution_value = ""

    def __init__(
        self,
        task: SWEBenchTaskInput,
        sandbox: SandboxExecutor,
        rules: RulesSwe,
        output_path: str = "solution.json",
        model_name: str | None = None,
        provider_url: str | None = None,
    ) -> None:
        """Initializes the loop for the Software Engineering Agent."""
        super().__init__(
            task=task,
            sandbox=sandbox,
            rules=rules,
            output_path=output_path,
            model_name=model_name,
            provider_url=provider_url,
        )
        self.issue_description = task.problem_statement
        self.prompt = SWEPromptBuilder(
            self.issue_description, tools_manual=sandbox.tools
        )

    def run(self) -> str:
        """Execute the iterative loop to resolve the SWE-bench issue."""
        start_time = time.time()
        steps_metric: list[StepMetrics] = []
        max_loop = self.rules.iterations
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
                feedback = SandboxOutputHandler.get_no_code_feedback("swebench")
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
                limit_error = self.limit_checker(steps_metric, start_time)
                if limit_error:
                    return self._save_failure(
                        steps_metric, start_time, limit_error
                    )
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

                self._save_solution(
                    status=True,
                    solution=str(solution),
                    steps=steps_metric,
                    total_time_seconds=time.time() - start_time,
                )
                return str(solution)

            # 2. Process feedback and update prompt
            if "edit_file" in code_for_sandbox:
                tests_passed = False

            has_patch = False
            if "run_tests" in code_for_sandbox:
                patch_res = self.sandbox.execute("print(get_patch())")
                has_patch = bool(patch_res.get("output", "").strip())

            feedback, tests_passed = (
                SandboxOutputHandler.get_swebench_feedback(
                    code_for_sandbox, sand_answer, tests_passed, has_patch
                )
            )
            self.prompt.add_model_response(
                f"```python\n{code_for_sandbox}\n```"
            )
            self.prompt.add_feedback(
                feedback, step=step, max_steps=max_loop
            )

            current_loop += 1

            limit_error = self.limit_checker(steps_metric, start_time)
            if limit_error:
                return self._save_failure(
                    steps_metric, start_time, limit_error
                )

        return self._save_failure(
            steps_metric,
            start_time,
            error="Iteration limit reached without solving the task.",
        )
