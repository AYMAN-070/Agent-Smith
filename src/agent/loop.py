from pathlib import Path
from typing import Any

from src.agent.prompt import PromptBuilder
from src.agent.prompt import SWEPromptBuilder
from src.agent.tools import run_tests
from src.llm.llm import LlmRequest, LlmResponse
from src.models import (
    MBPPTaskInput,
    SolutionOutput,
    StepMetrics,
    SWEBenchTaskInput,
)
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
        return "didnt succeed"


class SWEAgentLoop:
    def __init__(self, issue_description: str, sandbox: SandboxExecutor) -> None:
        """
        Initializes the loop for the Software Engineering Agent.
        mcp_tools: A dictionary of tools (read_file, run_command, etc.) provided by Dev A's MCP Client.
        """
        self.issue_description = issue_description
        self.sandbox = sandbox
        self.prompt = SWEPromptBuilder(issue_description)
        self.llm_request = LlmRequest()

    def run(self) -> str:
        max_loop = 30
        current_loop = 0
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
            print(code_for_sandbox)

            print("⚙️  [2/3] Executing in Sandbox...")
            sand_answer = self.sandbox.execute(code_for_sandbox)
            print("\n📤 [Sandbox Result]:", sand_answer)

            status = sand_answer.get("status")

            # 1. Final answer submitted by the agent
            if status == "final_answer":
                solution = sand_answer.get("answer")
                print("\n" + "=" * 50)
                print(f"✅ SUCCESS: Agent resolved the issue at iteration {step}!")
                print(f"Final Message:\n{solution}")
                print("=" * 50 + "\n")
                return str(solution)

            # 2. Code ran successfully (Agent used tools and printed results)
            elif status == "success":
                observation = sand_answer.get("output", "").strip()
                print("\n👁️  [Observation Output]:")
                print(observation if observation else "(No stdout output)")

                if not observation:
                    feedback = (
                        "Warning: Your code executed but produced no output. "
                        "Remember to use print() to see the results of your tools (e.g., print(read_file('main.py'))). "
                        "If you are finished, call final_answer('done')."
                    )
                else:
                    feedback = (
                        f"Sandbox Observation (stdout):\n{observation}\n\n"
                        "Analyze this output. Call another tool if you need more info, "
                        "or call final_answer('done') if the bug is fixed and tests pass."
                    )

                self.prompt.add_model_response(code_for_sandbox)
                self.prompt.add_feedback(feedback)

            # 3. Execution error in the agent's script
            else:
                error_trace = sand_answer.get("error") or "Unknown execution error."
                print("\n" + "!" * 50)
                print(f"❌ FAILED: Error detected in sandbox at iteration {step}:")
                print(f"{error_trace}")
                print("!" * 50 + "\n")

                self.prompt.add_model_response(code_for_sandbox)
                self.prompt.add_feedback(
                    f"[ATTENTION: Itération {step}/{max_loop}]\n"
                    f"Erreur d'exécution :\n{error_trace}\n"
                    "Corrige ton code et essaie encore. Dépêche-toi, tu n'as plus beaucoup d'essais !"
                )

            current_loop += 1

        print("\n" + "=" * 50)
        print("⚠️ FAILURE: Max iterations reached. The agent got stuck.")
        print("=" * 50 + "\n")
        return "FAILED"
