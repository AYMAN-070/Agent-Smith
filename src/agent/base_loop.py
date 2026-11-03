"""Base class for agent execution loops."""

import re
import time
from pathlib import Path
from typing import Any

from src.agent.sandbox_output_handler import SandboxOutputHandler
from src.llm.llm import LlmRequest, LlmResponse
from src.models import (
    MBPPTaskInput,
    SolutionOutput,
    StepMetrics,
    SWEBenchTaskInput,
)
from src.rules import RulesMbpp, RulesSwe
from src.sandbox.executor import SandboxExecutor


class BaseAgentLoop:
    """Base class providing common metrics, limits, and output handling for agent loops."""

    benchmark: str = ""
    failure_return_value: str = "didnt succeed"
    failure_solution_value: str = ""

    def __init__(
        self,
        task: MBPPTaskInput | SWEBenchTaskInput,
        sandbox: SandboxExecutor,
        rules: RulesMbpp | RulesSwe,
        output_path: str = "solution.json",
        model_name: str | None = None,
        provider_url: str | None = None,
    ) -> None:
        """Initialize the base agent loop with task data, sandbox, rules, and LLM."""
        self.task = task
        self.sandbox = sandbox
        self.rules = rules
        self.output_path = output_path
        self.llm_request = LlmRequest(model_name, provider_url)
        self.prompt: Any = None
        self.last_code: str | None = None
        self.repeat_count: int = 0
        self.read_history: list[tuple[str, int]] = []

    @property
    def task_id(self) -> str:
        """Return the unique task or instance identifier."""
        if hasattr(self.task, "task_id"):
            return str(self.task.task_id)
        if hasattr(self.task, "instance_id"):
            return str(self.task.instance_id)
        return ""

    def record_step(
        self,
        llm: LlmResponse,
        sandbox: dict[str, Any],
        step: int,
        executed_code: str | None = None,
    ) -> StepMetrics:
        """Record metrics and execution output for an iteration step."""
        raw_output = (
            sandbox.get("output")
            or sandbox.get("error")
            or sandbox.get("status", "")
        )
        code_input = executed_code if executed_code is not None else llm.code
        step_metric = StepMetrics(
            step=step,
            input_tokens=llm.input_tokens,
            output_tokens=llm.output_tokens,
            request_time_ms=llm.request_time_ms,
            api_url=llm.url,
            model_name=llm.model_name,
            llm_output=llm.llm_output,
            sandbox_input=code_input,
            sandbox_output=str(raw_output),
            retries=llm.retries,
        )
        return step_metric

    def record_no_code_step(self, llm: LlmResponse, step: int) -> StepMetrics:
        """Record step metrics for an iteration where no code was generated."""
        sand_answer = {
            "status": "error",
            "error": "No Python code found",
            "output": "",
        }
        return self.record_step(llm, sand_answer, step)

    def reset_repetition_tracker(self) -> None:
        """Reset repetition tracker when no code is generated."""
        self.last_code = None
        self.repeat_count = 0
        self.read_history.clear()

    def check_repetitive_code(self, code: str, step: int) -> str | None:
        """Detect duplicate executed code and return a warning if repeated."""
        normalized_code = "\n".join(
            line.strip()
            for line in code.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
        if self.last_code and normalized_code == self.last_code:
            self.repeat_count += 1
            action_hint = (
                "Revise your function logic or submit with "
                "`final_answer(...)`."
                if self.benchmark == "mbpp"
                else "Move forward immediately: apply your fix using "
                "`edit_file` or run tests with `print(run_tests())`."
            )
            return (
                f"[WARNING: REPETITIVE COMMAND DETECTED "
                f"(attempt {self.repeat_count + 1})]\n"
                f"You executed the EXACT same code as in step {step - 1}!\n"
                "You already received this observation above. "
                "Do NOT repeat the same queries or re-read the same "
                "file lines.\n"
                f"{action_hint}\n\n"
            )

        self.repeat_count = 0
        self.last_code = normalized_code

        # Check for repeated reads in the same ~20-line range
        read_match = re.search(
            r"read_file\(\s*['\"]([^'\"]+)['\"]\s*,\s*(\d+)", code
        )
        if read_match:
            filepath = read_match.group(1)
            start_line = int(read_match.group(2))
            recent_reads = sum(
                1
                for f, s in self.read_history
                if f == filepath and abs(s - start_line) <= 20
            )
            self.read_history.append((filepath, start_line))
            if recent_reads >= 2:
                return (
                    f"[WARNING: REPETITIVE FILE INSPECTION DETECTED]\n"
                    f"You have already read lines near {start_line} of "
                    f"'{filepath}' {recent_reads + 1} times!\n"
                    "The code is already in your observation history above. "
                    "Do NOT read it again.\n"
                    "Apply your fix NOW using `edit_file`.\n\n"
                )

        if "edit_file" in code:
            self.read_history.clear()

        return None

    def handle_no_code(
        self,
        llm_response: LlmResponse,
        step: int,
        max_loop: int,
    ) -> StepMetrics:
        """Handle prompt feedback and record step metrics when no code was generated."""
        print(
            "⚠️  [Warning]: No code block detected. Prompting LLM to format correctly."
        )
        self.reset_repetition_tracker()
        feedback = SandboxOutputHandler.get_no_code_feedback(self.benchmark)
        self.prompt.add_model_response(llm_response.llm_output)
        self.prompt.add_feedback(feedback, step=step, max_steps=max_loop)
        return self.record_no_code_step(llm_response, step)

    def limit_checker(
        self,
        steps: list[StepMetrics],
        start_time: float | None = None,
        is_final_answer: bool = False,
    ) -> str | None:
        """Check if any token, iteration, or timeout limit defined in rules is exceeded."""
        total_input = sum(step.input_tokens for step in steps)
        if total_input > self.rules.input_tokens:
            msg = f"Input token limit exceeded: {total_input} > {self.rules.input_tokens}"
            print(f"⚠️ {msg}")
            return msg

        total_output = sum(step.output_tokens for step in steps)
        if total_output > self.rules.output_tokens:
            msg = f"Output token limit exceeded: {total_output} > {self.rules.output_tokens}"
            print(f"⚠️ {msg}")
            return msg

        if start_time is not None:
            elapsed_time = time.time() - start_time
            if elapsed_time > self.rules.timeout:
                msg = f"Timeout exceeded: {elapsed_time:.2f}s > {self.rules.timeout}s"
                print(f"⚠️ {msg}")
                return msg

        max_allowed_iterations = (
            self.rules.iterations
            if is_final_answer
            else self.rules.iterations - 1
        )
        if len(steps) > max_allowed_iterations:
            msg = f"Iteration limit reached: {len(steps)} >= {self.rules.iterations}"
            print(f"⚠️ {msg}")
            return msg

        return None

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
        system_instruction = (
            self.prompt.system_instruction if self.prompt else ""
        )

        return SolutionOutput(
            task_id=self.task_id,
            benchmark=self.benchmark,
            success=status,
            solution=solution,
            iterations=total_iteration,
            total_requests=total_requests,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_time_seconds=total_time_seconds,
            steps=steps,
            system_prompt=system_instruction,
            error=error,
        )

    def _save_solution(
        self,
        status: bool,
        solution: str,
        steps: list[StepMetrics],
        total_time_seconds: float,
        error: str | None = None,
    ) -> SolutionOutput:
        """Build and write solution output to output_path."""
        solution_output = self.build_solution_output(
            status=status,
            solution=solution,
            steps=steps,
            total_time_seconds=total_time_seconds,
            error=error,
        )
        out_path = Path(self.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            solution_output.model_dump_json(indent=2), encoding="utf-8"
        )
        return solution_output

    def _save_checkpoint(
        self,
        steps: list[StepMetrics],
        start_time: float,
    ) -> None:
        """Save intermediate progress to solution.json after each iteration."""
        self._save_solution(
            status=False,
            solution=self.failure_solution_value,
            steps=steps,
            total_time_seconds=time.time() - start_time,
            error="Process interrupted or timed out before completion.",
        )

    def try_auto_submit(
        self,
        steps_metric: list[StepMetrics],
        start_time: float,
    ) -> str | None:
        """Attempt to auto-submit solution if conditions are met. Default no-op."""
        return None

    def _save_failure(
        self,
        steps: list[StepMetrics],
        start_time: float,
        error: str | None = None,
    ) -> str:
        """Build and save failure output to output_path and return failure status."""
        auto_solution = self.try_auto_submit(steps, start_time)
        if auto_solution is not None:
            return auto_solution

        self._save_solution(
            status=False,
            solution=self.failure_solution_value,
            steps=steps,
            total_time_seconds=time.time() - start_time,
            error=error,
        )
        return self.failure_return_value

    def handle_shutdown(
        self,
        exc: BaseException,
        steps_metric: list[StepMetrics],
        start_time: float,
    ) -> None:
        """Perform proper shutdown when program flow exceptions occur."""
        exc_name = type(exc).__name__
        print(
            f"\n🛑 Execution interrupted by {exc_name}. "
            "Performing proper agent loop shutdown..."
        )
        self._save_failure(
            steps_metric,
            start_time,
            error=f"Execution interrupted by {exc_name}",
        )
        self.sandbox.close()
