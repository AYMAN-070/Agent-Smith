from src.agent.prompt import Prompt
from src.llm.llm import llm
from src.models import MBPPTaskInput
from src.sandbox.executor import SandboxExecutor


class Loop:
    def __init__(self, task: MBPPTaskInput) -> None:
        self.task = task
        self.sandbox = SandboxExecutor()
        self.prompt = Prompt(task)

    def loop(self) -> str:
        max_loop = 10
        current_loop = 0
        print("\n" + "=" * 50)
        print("🚀 START AGENT LOOP")
        print("=" * 50)

        while current_loop < max_loop:
            step = current_loop + 1
            print(f"\n--- [ITERATION {step}/{max_loop}] ---")
            
            print("\n🤖 [1/3] Calling LLM with current prompt/history...")
            answer = llm(self.prompt)
            print("\n📥 [LLM Response / Generated Code]:")
            print(answer)

            code_for_sandbox = self.code_to_test(answer)
            print("\n📦 [2/3] Prepared Code For Sandbox (Function + Tests):")
            print(code_for_sandbox)

            print("⚙️  [3/3] Executing in Sandbox...")
            sand_answer = self.sandbox.execute(code_for_sandbox)
            print("\n📤 [Sandbox Result]:", sand_answer)

            if sand_answer.get("status") == "success":
                print("\n" + "=" * 50)
                print(f"✅ SUCCESS: Task solved at iteration {step}!")
                print("=" * 50 + "\n")
                return answer
            else:
                error_trace = sand_answer.get("error") or sand_answer.get("output", "Test failed")
                print("\n" + "!" * 50)
                print(f"❌ FAILED: Error detected in sandbox at iteration {step}:")
                print("-" * 50)
                print(f"{error_trace}")
                print("-" * 50)
                print("🔄 Feeding code and error trace back to prompt for next iteration...")
                print("!" * 50 + "\n")

                # Send original answer to model history and error trace to user history
                self.prompt.model_prompt(answer)
                self.prompt.trace_prompt(error_trace)
                current_loop += 1

        print("\n" + "=" * 50)
        print("⚠️ FAILURE: Max iterations reached without solving the task.")
        print("=" * 50 + "\n")
        return "didnt succed"

    def code_to_test(self, code: str) -> str:
        clean_code = code.strip()
        tests = "\n".join(self.prompt.test_list)
        imports = "\n".join(self.task.test_imports)
        if imports:
            clean_code = f"{imports}\n\n{clean_code}"
        return f"{clean_code}\n\n{tests}\n"
