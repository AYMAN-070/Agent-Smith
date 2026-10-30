#!/usr/bin/env python3
"""
MCP Server for MBPP benchmark tools.
Exposes tools, resources, and prompts over standard input/output (stdio)
according to the Model Context Protocol (JSON-RPC 2.0).
"""

import json
import sys
from typing import Any

MBPP_GUIDELINES_TEXT = """# MBPP (Mostly Basic Python Problems) Guidelines

### 1. Goal
Solve algorithmic challenges by implementing clean, correct, and self-contained Python 3.10 functions.

### 2. Implementation Rules
- Function Signature: Must strictly match the task prompt and assertions.
- Allowed Dependencies: Only Python standard library modules (e.g., math, collections, itertools, re).
- Purity: Functions must be self-contained without unintended side effects.

### 3. Testing Workflow
- Validate using the run_tests(code, test_list) tool.
- Ensure all test assertions pass before submitting.

### 4. Submission
- Call final_answer(solution_code) with your solution Python code string.
"""

RESOURCES_SCHEMA = [
    {
        "uri": "mbpp://guidelines",
        "name": "MBPP Benchmark Guidelines",
        "description": "Rules, constraints, and best practices for solving MBPP tasks",
        "mimeType": "text/markdown",
    }
]

PROMPTS_SCHEMA = [
    {
        "name": "solve_mbpp_task",
        "description": "Template prompt to guide solving an MBPP algorithmic task",
        "arguments": [
            {
                "name": "task_prompt",
                "description": "The description of the function to implement",
                "required": True,
            }
        ],
    }
]

TOOLS_SCHEMA = [
    {
        "name": "run_tests",
        "description": (
            "Run candidate Python code against a list of test assertions "
            "and return a JSON summary ('success': bool, 'output': str)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Candidate Python function code",
                },
                "test_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of assert statements (e.g. ['assert add(1, 2) == 3'])",
                },
            },
            "required": ["code", "test_list"],
        },
    }
]


def run_tests(code: str, test_list: list[str]) -> str:
    """Run candidate Python code against a list of test assertions."""
    execution_namespace: dict[str, Any] = {}
    try:
        exec(code, execution_namespace)
    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "output": f"Code execution failed ({type(e).__name__}): {e}",
            }
        )

    passed = 0
    total = len(test_list)
    failed_details: list[str] = []

    for assertion in test_list:
        try:
            exec(assertion, execution_namespace)
            passed += 1
        except AssertionError:
            failed_details.append(f"Assertion failed: {assertion}")
        except Exception as e:
            failed_details.append(
                f"Test error on '{assertion}' ({type(e).__name__}): {e}"
            )

    if passed == total:
        return json.dumps(
            {
                "success": True,
                "output": f"All {total} tests passed successfully.",
            }
        )
    else:
        return json.dumps(
            {
                "success": False,
                "output": f"{passed}/{total} tests passed. Failures:\n"
                + "\n".join(failed_details),
            }
        )


def send_response(response: dict[str, Any]) -> None:
    """Send JSON-RPC response to stdout."""
    try:
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()
    except Exception as e:
        print(f"Error sending MCP response: {e}", file=sys.stderr)


def handle_request(line: str) -> None:
    """Process a single JSON-RPC 2.0 request line."""
    try:
        request = json.loads(line)
    except json.JSONDecodeError:
        return

    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    try:
        # Protocol initialization
        if method == "initialize":
            send_response(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                            "resources": {},
                            "prompts": {},
                        },
                        "serverInfo": {
                            "name": "mcp_tools_mbpp",
                            "version": "1.0.0",
                        },
                    },
                }
            )
            return

        # Client notification after initialization
        if method == "notifications/initialized":
            return

        # List available tools
        if method == "tools/list":
            send_response(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": TOOLS_SCHEMA,
                    },
                }
            )
            return

        # Execute a tool
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "run_tests":
                code = arguments.get("code", "")
                test_list = arguments.get("test_list", [])
                output = run_tests(code, test_list)

                send_response(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": output,
                                }
                            ],
                        },
                    }
                )
                return
            else:
                send_response(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method/Tool '{tool_name}' not found.",
                        },
                    }
                )
                return

        # List available resources
        if method == "resources/list":
            send_response(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "resources": RESOURCES_SCHEMA,
                    },
                }
            )
            return

        # Read a resource
        if method == "resources/read":
            uri = params.get("uri")
            if uri == "mbpp://guidelines":
                send_response(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": "text/markdown",
                                    "text": MBPP_GUIDELINES_TEXT,
                                }
                            ],
                        },
                    }
                )
                return
            else:
                send_response(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32602,
                            "message": f"Resource '{uri}' not found.",
                        },
                    }
                )
                return

        # List available prompts
        if method == "prompts/list":
            send_response(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "prompts": PROMPTS_SCHEMA,
                    },
                }
            )
            return

        # Get a prompt
        if method == "prompts/get":
            prompt_name = params.get("name")
            prompt_args = params.get("arguments", {})
            if prompt_name == "solve_mbpp_task":
                task_desc = prompt_args.get("task_prompt", "")
                send_response(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "description": "Template prompt to guide solving an MBPP algorithmic task",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {
                                        "type": "text",
                                        "text": (
                                            f"Please write a Python function that solves the following problem:\n"
                                            f"{task_desc}\n\n"
                                            "Make sure your function passes all test assertions and call "
                                            "final_answer(code) when done."
                                        ),
                                    },
                                }
                            ],
                        },
                    }
                )
                return
            else:
                send_response(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32602,
                            "message": f"Prompt '{prompt_name}' not found.",
                        },
                    }
                )
                return

        # Unknown method
        if req_id is not None:
            send_response(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found.",
                    },
                }
            )
    except Exception as e:
        if req_id is not None:
            send_response(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32603,
                        "message": f"Internal MCP error: {e}",
                    },
                }
            )


def main() -> None:
    """Main loop reading JSON-RPC requests line by line from stdin."""
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                handle_request(line)
            except Exception as e:
                print(f"Error handling request: {e}", file=sys.stderr)
    except Exception as err:
        print(f"MBPP MCP server error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
