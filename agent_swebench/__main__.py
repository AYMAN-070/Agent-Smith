"""CLI entry point for running the SWE-bench agent."""

import argparse
import atexit
import os
import shlex
import signal
import sys
from pathlib import Path
from typing import Any

from src.agent.loop import SWEAgentLoop
from src.docker_handler import DockerContainer
from src.models import SWEBenchTaskInput
from src.rules import RulesSwe
from src.sandbox.executor import SandboxExecutor


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the SWE-bench agent."""
    parser = argparse.ArgumentParser(description="Agent Smith SWE-bench CLI")
    parser.add_argument(
        "--task-file",
        type=str,
        required=True,
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
    parser.add_argument(
        "--max_iterations",
        "--max-iterations",
        type=int,
        default=None,
        help="Optional maximum loop iterations override",
    )
    return parser.parse_args()


def main() -> None:
    """Run the SWE-bench agent workflow."""
    args = parse_arguments()
    task_content = Path(args.task_file).read_text(encoding="utf-8")
    task = SWEBenchTaskInput.model_validate_json(task_content)
    docker_container = DockerContainer(task.docker_image)
    sandbox = SandboxExecutor()
    rules = RulesSwe(args.max_iterations)
    atexit.register(docker_container.stop_and_remove)

    def clean_exit(signum: int, frame: Any) -> None:
        """Handle termination signals and cleanup container and sandbox."""
        print("\nKill signal received, cleaning in progress...")
        docker_container.stop_and_remove()
        sandbox.close()
        sys.exit(143)

    signal.signal(signal.SIGTERM, clean_exit)
    signal.signal(signal.SIGINT, clean_exit)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, clean_exit)

    try:
        container_id = docker_container.start()
        docker_container.setup_eval_script(task.eval_script)
        os.environ["SWE_CONTAINER_ID"] = container_id

        if args.mcp_server:
            sandbox.connect_mcp(server_url=args.mcp_server)
        elif args.mcp_stdio:
            sandbox.connect_mcp(stdio_cmd=args.mcp_stdio)
        else:
            root_dir = Path(__file__).resolve().parent.parent
            default_server = root_dir / "mcp_tools_swebench.py"
            cmd = f"python3 {shlex.quote(str(default_server))}"
            sandbox.connect_mcp(stdio_cmd=cmd)

        agent = SWEAgentLoop(
            task=task,
            sandbox=sandbox,
            output_path=args.output,
            model_name=args.model_name,
            provider_url=args.provider_url,
            rules=rules,
        )
        agent.run()
    except Exception as err:
        print(f"\n{err}", file=sys.stderr)
        sys.exit(1)
    finally:
        sandbox.close()
        docker_container.stop_and_remove()


if __name__ == "__main__":
    main()
