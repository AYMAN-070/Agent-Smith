import re


class ExtractCode:
    def __init__(self, llm_text) -> None:
        self.text = llm_text

    def code(self, llm_text: str) -> str:
        pattern = r"```(?:python|py)?\s*\n(.*?)```"
        match = re.search(pattern, self.text, re.DOTALL | re.IGNORECASE)
        if match:
            python_code = match.group(1).strip()
            return python_code
        return ""
