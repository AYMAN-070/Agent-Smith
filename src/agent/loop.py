from pathlib import Path
from typing import Any

from src.agent.prompt import PromptBuilder
from src.agent.tools import run_tests
from src.llm.llm import LlmRequest, LlmResponse
from src.models import MBPPTaskInput, SolutionOutput, StepMetrics
from src.sandbox.executor import SandboxExecutor


class AgentLoop:
    def __init__(self, task: MBPPTaskInput) -> None:
        self.task = task
        self.sandbox = SandboxExecutor()
        self.sandbox.register_custom_module(
            "agent_tools",
            {
                "run_tests": run_tests,
                "TESTS": self.task.test_list,
            },
        )
        self.prompt = PromptBuilder(task)
        self.llm_request = LlmRequest()

    def run(self) -> None:
        steps_metric = []
        max_loop = 10
        current_loop = 0
        print("\n" + "=" * 50)
        print("🚀 START AGENT LOOP")
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
            print(code_for_sandbox)

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

                solu = self.build_solution_output(
                    True, str(solution), steps_metric
                )
                Path("solution.json").write_text(
                    solu.model_dump_json(indent=2), encoding="utf-8"
                )
                return

            # 2. Code ran successfully (e.g., agent printed test results)
            elif status == "success":
                observation = sand_answer.get("output", "").strip()
                print("\n👁️  [Observation Output]:")
                print(observation if observation else "(No stdout output)")

                if not observation:
                    feedback = (
                        "Warning: You defined a function but did NOT print"
                        "and any test results and"
                        " did NOT call final_answer().\n"
                        "To proceed, you MUST either test your function:\n"
                        "  from agent_tools import run_tests, TESTS\n"
                        "  print(run_tests(candidate, TESTS))\n"
                        "Or call final_answer(solution_code)"
                        " if you are sure it works."
                    )
                else:
                    feedback = (
                        f"Sandbox Observation (stdout):\n{observation}\n\n"
                        "If all tests passed, call"
                        " final_answer(your_solution_code).\n"
                        "If tests failed, modify your"
                        " implementation and re-test with run_tests."
                    )

                self.prompt.add_model_response(code_for_sandbox)
                self.prompt.add_error_feedback(feedback)

            # 3. Execution error or timeout
            else:
                error_trace = (
                    sand_answer.get("error")
                    or "Execution failed without details."
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

                self.prompt.add_model_response(code_for_sandbox)
                self.prompt.add_error_feedback(
                    f"Sandbox Error:\n{error_trace}"
                )

            current_loop += 1

        print("\n" + "=" * 50)
        print("⚠️ FAILURE: Max iterations reached without solving the task.")
        print("=" * 50 + "\n")
        solu = self.build_solution_output(True, str(solution), steps_metric)
        Path("solution.json").write_text(
            solu.model_dump_json(indent=2), encoding="utf-8"
        )
        return

    def record_step(
        self, llm: LlmResponse, sandbox: dict[str, Any], step: int
    ) -> StepMetrics:
        step_metric = StepMetrics(
            step=step,
            input_tokens=llm.input_tokens,
            output_tokens=llm.output_tokens,
            request_time_ms=llm.request_time_ms,
            api_url=llm.url,
            model_name=llm.model_name,
            llm_output=llm.llm_output,
            sandbox_input=llm.code,
            sandbox_output=sandbox["status"],
            retries=llm.retries,
        )
        return step_metric

    def build_solution_output(
        self, status: bool, solution: str, steps: list[StepMetrics]
    ) -> SolutionOutput:
        total_iteration = len(steps)
        total_requests = len(steps) + sum(s.retries for s in steps)
        total_input_tokens = sum(s.input_tokens for s in steps)
        total_output_tokens = sum(s.output_tokens for s in steps)
        total_time_seconds = sum(s.request_time_ms for s in steps) / 1000.0

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
            error=None,
        )
        return solution_output
