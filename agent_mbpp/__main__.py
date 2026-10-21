import argparse
from pathlib import Path

from src.agent.loop import MBPPAgentLoop
from src.agent.tools import run_tests
from src.mcp.client import HttpMCPClient, MCPClient
from src.mcp.wrappers import create_tool_wrappers
from src.models import MBPPTaskInput
from src.sandbox.executor import SandboxExecutor


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent Smith MBPP CLI")
    parser.add_argument(
        "--task-file",
        type=str,
        required=True,
        help="Path to MBPP task.json",
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


def main() -> None:
    args = parse_arguments()
    task_content = Path(args.task_file).read_text(encoding="utf-8")
    task = MBPPTaskInput.model_validate_json(task_content)

    mcp_client = None
    if args.mcp_server:
        mcp_client = HttpMCPClient(args.mcp_server)
        mcp_client.start()
    elif args.mcp_stdio:
        mcp_client = MCPClient(args.mcp_stdio)
        mcp_client.start()
    else:
        root_dir = Path(__file__).resolve().parent.parent
        server_script = root_dir / "mcp_tools_mbpp.py"
        if server_script.exists():
            mcp_client = MCPClient(f"python3 {server_script}")
            mcp_client.start()

    try:
        sandbox = SandboxExecutor()

        if mcp_client and getattr(mcp_client, "tools", None):
            tool_wrappers = create_tool_wrappers(mcp_client)
        else:
            tool_wrappers = {
                "run_tests": run_tests,
                "TESTS": task.test_list,
            }

        sandbox.register_custom_module("agent_tools", tool_wrappers)
        sandbox.custom_modules.update(tool_wrappers)

        agent = MBPPAgentLoop(
            task=task,
            sandbox=sandbox,
            mcp_client=mcp_client,
        )
        agent.run()
    finally:
        if mcp_client:
            mcp_client.stop()


if __name__ == "__main__":
    main()
