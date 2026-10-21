import argparse
import json
import os
import sys
from pathlib import Path

from src.agent.loop import SWEAgentLoop
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
    print("STARTING SWE-BENCH AGENT")
    print("===" * 15)

    args = parse_arguments()
    issue_description = load_issue(args.task_file)

    sandbox = SandboxExecutor()

    if args.mcp_server:
        sandbox.connect_mcp(server_url=args.mcp_server)
    elif args.mcp_stdio:
        sandbox.connect_mcp(stdio_cmd=args.mcp_stdio)
    else:
        root_dir = Path(__file__).resolve().parent.parent
        default_server = root_dir / "mcp_tools_swebench.py"
        sandbox.connect_mcp(stdio_cmd=f"python3 {default_server}")

    try:
        agent_loop = SWEAgentLoop(
            issue_description=issue_description,
            sandbox=sandbox,
        )
        result = agent_loop.run()
        print("\n🏁 FINAL RESULT:", result)
    finally:
        sandbox.close()


if __name__ == "__main__":
    main()
