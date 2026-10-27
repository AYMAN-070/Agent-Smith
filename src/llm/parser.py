import json
import re
from typing import Any


class ResponseParser:
    def __init__(self, llm_output: str) -> None:
        self.code: str = self.output_sorting(llm_output)

    @classmethod
    def parse(cls, llm_output: str) -> str:
        return cls(llm_output).code

    def _parse_val(self, val_str: str) -> Any:
        clean_val = val_str.strip()
        try:
            return json.loads(clean_val)
        except Exception:
            return clean_val

    def _format_call(self, func_name: str, args: Any) -> str:
        if isinstance(args, dict):
            args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
        else:
            args_str = repr(args) if args else ""
        return f"{func_name}({args_str})"

    def hermes(self, raw_json: str) -> str:
        try:
            data = json.loads(raw_json)
            func_name = data.get("name", "")
            args = data.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    pass
            if func_name:
                return self._format_call(func_name, args)
        except Exception:
            pass
        return ""

    def xml(self, name: str, params_str: str) -> str:
        args: dict[str, Any] = {}
        param_pattern = (
            r'<parameter(?:\s+name=["\'](?P<key>[^"\']+)["\'])?>'
            r"(?P<val>.*?)</parameter>"
        )
        param_matches = list(re.finditer(param_pattern, params_str, re.DOTALL))

        if param_matches:
            for p in param_matches:
                key = p.group("key")
                val = p.group("val")
                if key:
                    args[key.strip()] = self._parse_val(val)
                elif "=" in val:
                    k, v = val.split("=", 1)
                    args[k.strip()] = self._parse_val(v)
                else:
                    args["param"] = self._parse_val(val)
        else:
            child_pattern = r"<([a-zA-Z0-9_]+)>(.*?)</\1>"
            for k, v in re.findall(child_pattern, params_str, re.DOTALL):
                args[k.strip()] = self._parse_val(v)

        return self._format_call(name, args)

    def react(self, action: str, raw_input: str) -> str:
        clean_input = re.sub(r"^```[a-zA-Z]*\n?|```$", "", raw_input).strip()
        try:
            args = json.loads(clean_input)
        except Exception:
            args = clean_input
        return self._format_call(action, args)

    def output_sorting(self, llm_output: str) -> str:
        # 1. Hermes / JSON tool calls
        hermes_pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
        match = re.search(
            hermes_pattern, llm_output, re.DOTALL | re.IGNORECASE
        )
        if match:
            return self.hermes(match.group(1).strip())

        # 2. XML tool calls (Anthropic-style)
        xml_pattern = (
            r'<invoke\s+name=["\'](?P<name>[^"\']+)["\']>'
            r"(?P<params>.*?)</invoke>"
        )
        match = re.search(xml_pattern, llm_output, re.DOTALL | re.IGNORECASE)
        if match:
            return self.xml(match.group("name").strip(), match.group("params"))

        # 3. ReAct format (Action: / Action Input:)
        react_pattern = (
            r"Action:\s*([a-zA-Z0-9_]+)\s*\nAction Input:\s*(.+?)"
            r"(?=\nAction:|\nObservation:|\nThought:|$)"
        )
        match = re.search(react_pattern, llm_output, re.DOTALL | re.IGNORECASE)
        if match:
            return self.react(match.group(1).strip(), match.group(2).strip())

        # 4. Blocs Python classiques (avec ``` ou <end_code>)
        py_pattern = r"```(?:python|py)?\s*\n(.*?)(?:```|<end_code>)"
        match = re.search(py_pattern, llm_output, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return ""
