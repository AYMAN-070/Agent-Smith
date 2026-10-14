import re


class CodeParser:
    def __init__(self, llm_text: str) -> None:
        self.text = llm_text

    def parse(self) -> str:
        pattern = r"```(?:python|py)?\s*\n(.*?)```"
        match = re.search(pattern, self.text, re.DOTALL | re.IGNORECASE)
        if match:
            python_code = match.group(1).strip()
            return python_code
        return ""
