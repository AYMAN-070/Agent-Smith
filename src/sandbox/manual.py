from collections.abc import Mapping, Sequence
from typing import Any


def format_tool_signature(tool: Mapping[str, Any]) -> str:
    """Formats a tool schema into a human-readable Python function signature."""
    name = tool.get("name", "unknown_tool")
    schema = tool.get("inputSchema", {})
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    param_parts: list[str] = []
    for prop_name, prop_info in properties.items():
        type_str = prop_info.get("type", "Any")
        if type_str == "string":
            py_type = "str"
        elif type_str == "array":
            py_type = "list"
        elif type_str == "integer":
            py_type = "int"
        elif type_str == "boolean":
            py_type = "bool"
        elif type_str == "object":
            py_type = "dict"
        else:
            py_type = "Any"

        if prop_name in required:
            param_parts.append(f"{prop_name}: {py_type}")
        else:
            param_parts.append(f"{prop_name}: {py_type} = None")

    params_joined = ", ".join(param_parts)
    return f"{name}({params_joined})"


DEFAULT_MBPP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "run_tests",
        "description": "Runs candidate code against test assertions and returns success status and output.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Candidate Python code string",
                },
                "test_list": {
                    "type": "array",
                    "description": "List of assert statement strings",
                },
            },
            "required": ["code", "test_list"],
        },
    }
]


def generate_tools_manual(tools: Sequence[Mapping[str, Any]] | None = None) -> str:
    """Dynamically generates documentation for all available tools

    to be injected into the LLM system prompt.
    Section V.2.5 of Agent Smith specification.
    """
    resolved_tools = tools if tools is not None else DEFAULT_MBPP_TOOLS
    lines: list[str] = [
        "AVAILABLE TOOLS IN SANDBOX:",
        "All tools are available as global Python functions (no import required).",
        "",
    ]

    for tool in resolved_tools:
        sig = format_tool_signature(tool)
        desc = tool.get("description", "No description provided.")
        lines.append(f"1. `{sig}`")
        lines.append(f"   {desc}")

        props = tool.get("inputSchema", {}).get("properties", {})
        if props:
            lines.append("   Parameters:")
            for p_name, p_info in props.items():
                p_desc = p_info.get("description", "")
                lines.append(
                    f"     - {p_name} ({p_info.get('type', 'Any')}): {p_desc}"
                )
        lines.append("")

    # Built-in tool always present in sandbox
    lines.append("BUILT-IN CONTROL FUNCTION:")
    lines.append("`final_answer(answer: Any)`")
    lines.append(
        "Call this function to submit your final answer and complete the task."
    )
    lines.append(
        "For MBPP: pass the python solution string. For SWE-bench: pass the git patch."
    )

    return "\n".join(lines)
