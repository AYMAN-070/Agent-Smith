import argparse
import json
import os
import sys
from pathlib import Path

from src.agent.loop import SWEAgentLoop
from src.mcp.client import HttpMCPClient, MCPClient
from src.mcp.wrappers import create_tool_wrappers
from src.sandbox.executor import SandboxExecutor


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent Smith SWE-bench CLI")
    parser.add_argument(
        "--task-file",
        type=str,
        default="task.json",
        help="Path to SWE-bench task.json",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="solution.json",
        help="Path to solution.json output",
    )
    parser.add_argument(
        "--mcp-stdio",
        type=str,
        default=None,
        help="Command to launch MCP server via stdio",
    )
    parser.add_argument(
        "--mcp-server",
        type=str,
        default=None,
        help="URL for remote HTTP MCP server",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=None,
        help="Optional model name override",
    )
    parser.add_argument(
        "--provider-url",
        type=str,
        default=None,
        help="Optional provider API URL",
    )
    return parser.parse_args()


def load_issue(filepath: str) -> str:
    """Load bug description from JSON file."""
    if not os.path.exists(filepath):
        print(f"Error: Could not find {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("problem_statement", "No description provided.")


def main() -> None:
    print("===" * 15)
    print("🤖 STARTING SWE-BENCH AGENT")
    print("===" * 15)

    args = parse_arguments()
    issue_description = load_issue(args.task_file)

    mcp_client = None
    if args.mcp_server:
        mcp_client = HttpMCPClient(args.mcp_server)
        mcp_client.start()
    elif args.mcp_stdio:
        mcp_client = MCPClient(args.mcp_stdio)
        mcp_client.start()
    else:
        root_dir = Path(__file__).resolve().parent.parent
        server_script = root_dir / "mcp_tools_swebench.py"
        if not server_script.exists():
            print(
                f"Error: MCP server script not found at {server_script}",
                file=sys.stderr,
            )
            sys.exit(1)
        mcp_client = MCPClient(f"python3 {server_script}")
        mcp_client.start()

    try:
        mcp_tools = create_tool_wrappers(mcp_client)

        sandbox = SandboxExecutor()
        sandbox.register_custom_module("agent_tools", mcp_tools)
        sandbox.custom_modules.update(mcp_tools)

        agent_loop = SWEAgentLoop(
            issue_description=issue_description,
            sandbox=sandbox,
            mcp_client=mcp_client,
        )
        result = agent_loop.run()
        print("\n🏁 FINAL RESULT:", result)

    finally:
        if mcp_client:
            mcp_client.stop()


if __name__ == "__main__":
    main()
