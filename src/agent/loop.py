from src.agent.prompt import Prompt

from src.llm.llm import llm
from src.models import MBPPTaskInput
from src.sandbox.executor import SandboxExecutor


class Loop:
    def __init__(self, task: MBPPTaskInput) -> None:
        self.task = task
        self.sandbox = SandboxExecutor()
        self.prompt = Prompt(task)

    def loop(self):
        # memory = []
        # max_loop = 10
        # current_loop = 0
        print("start loop")
        answer = llm(self.prompt)
        code_for_sandbox = self.code_to_test(answer)
        print("code_for_sandbox")
        # string = (
        #     "  def maximum(a, b):\n"
        #     "    return a if a > b else b\n"
        #     "print(maximum(15, 8))\n"
        #     "assert maximum(1, 2) == 2\n"
        # )

        sand_answer = self.sandbox.execute(code_for_sandbox)
        print(sand_answer)
        # return answer
        # return self.prompt
        # while current_loop < max_loop:
        #     self.prompt.task_definition
        #     current_loop += 1

    def code_to_test(self, code: str) -> str:
        clean_code = code.strip()
        tests = "\n".join(self.prompt.test_list)
        imports = "\n".join(self.task.test_imports)
        if imports:
            clean_code = f"{imports}\n\n{clean_code}"
        return f"{clean_code}\n\n{tests}\n"
