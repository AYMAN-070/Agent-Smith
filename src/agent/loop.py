from src.agent.prompt import Prompt
from src.llm.llm import llm
from src.models import MBPPTaskInput
from src.sandbox.sandbox_testing import LocalSandbox


class Loop:
    def __init__(self, task: MBPPTaskInput) -> None:
        self.sandbox = LocalSandbox()
        self.prompt = Prompt(task)

    def loop(self):
        # memory = []
        # max_loop = 10
        # current_loop = 0
        print("start loop")
        answer = llm(self.prompt)
        print("answer ok")
        sand_answer = self.sandbox.execute(answer)
        print(sand_answer)
        return answer
        # return self.prompt
        # while current_loop < max_loop:
        #     self.prompt.task_definition
        #     current_loop += 1
