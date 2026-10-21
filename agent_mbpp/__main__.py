import argparse
from pathlib import Path
import shlex

from src.agent.loop import MBPPAgentLoop
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

    sandbox = SandboxExecutor()

    if args.mcp_server:
        sandbox.connect_mcp(server_url=args.mcp_server)
    elif args.mcp_stdio:
        sandbox.connect_mcp(stdio_cmd=args.mcp_stdio)
    else:
        root_dir = Path(__file__).resolve().parent.parent
        default_server = root_dir / "mcp_tools_mbpp.py"
        cmd = f"python3 {shlex.quote(str(default_server))}"
        sandbox.connect_mcp(stdio_cmd=cmd)

    try:
        agent = MBPPAgentLoop(
            task=task,
            sandbox=sandbox,
            output_path=args.output,
            model_name=args.model_name,
            provider_url=args.provider_url,
        )
        agent.run()
    finally:
        sandbox.close()


if __name__ == "__main__":
    main()
