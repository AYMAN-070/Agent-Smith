#!/usr/bin/env python3
"""
MCP Server for MBPP benchmark tools.
Exposes tools over standard input/output (stdio) according to the Model Context Protocol (JSON-RPC 2.0).
"""

import sys
import json
from typing import Any, Dict, List


def run_tests(code: str, test_list: List[str]) -> str:
    """Run candidate Python code against a list of test assertions."""
    execution_namespace: Dict[str, Any] = {}
    try:
        exec(code, execution_namespace)
    except Exception as e:
        return json.dumps({
            "success": False,
            "output": f"Code execution failed ({type(e).__name__}): {e}"
        })

    passed = 0
    total = len(test_list)
    failed_details: List[str] = []

    for assertion in test_list:
        try:
            exec(assertion, execution_namespace)
            passed += 1
        except AssertionError:
            failed_details.append(f"Assertion failed: {assertion}")
        except Exception as e:
            failed_details.append(f"Test error on '{assertion}' ({type(e).__name__}): {e}")

    if passed == total:
        return json.dumps({
            "success": True,
            "output": f"All {total} tests passed successfully."
        })
    else:
        return json.dumps({
            "success": False,
            "output": f"{passed}/{total} tests passed. Failures:\n" + "\n".join(failed_details)
        })


TOOLS_SCHEMA = [
    {
        "name": "run_tests",
        "description": "Run candidate Python code against a list of test assertions and return a JSON summary ('success': bool, 'output': str).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Candidate Python function code"
                },
                "test_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of assert statements (e.g. ['assert add(1, 2) == 3'])"
                }
            },
            "required": ["code", "test_list"]
        }
    }
]


def send_response(response: Dict[str, Any]) -> None:
    """Send JSON-RPC response to stdout."""
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def handle_request(line: str) -> None:
    """Process a single JSON-RPC 2.0 request line."""
    try:
        request = json.loads(line)
    except json.JSONDecodeError:
        return

    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    # Protocol initialization
    if method == "initialize":
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "mcp_tools_mbpp",
                    "version": "1.0.0"
                }
            }
        })
        return

    # Client notification after initialization
    if method == "notifications/initialized":
        return

    # List available tools
    if method == "tools/list":
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS_SCHEMA
            }
        })
        return

    # Execute a tool
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "run_tests":
            code = arguments.get("code", "")
            test_list = arguments.get("test_list", [])
            output = run_tests(code, test_list)

            # MCP spec requires content array in tool call result
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": output
                        }
                    ]
                }
            })
            return
        else:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method/Tool '{tool_name}' not found."
                }
            })
            return

    # Unknown method
    if req_id is not None:
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found."
            }
        })


def main() -> None:
    """Main loop reading JSON-RPC requests line by line from stdin."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        handle_request(line)


if __name__ == "__main__":
    main()
