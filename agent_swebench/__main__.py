import argparse
import os
from pathlib import Path
import signal
import sys
import shlex
from typing import Any

from src.agent.loop import SWEAgentLoop
from src.docker_handler import DockerContainer
from src.models import SWEBenchTaskInput
from src.sandbox.executor import SandboxExecutor


def parse_arguments() -> argparse.Namespace:
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
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    task_content = Path(args.task_file).read_text(encoding="utf-8")
    # Optional AgentArgs instance (currently unused)
    # parser = AgentArgs("Agent SWE")
    # task_content = Path(parser.task_file).read_text(encoding="utf-8")
    task = SWEBenchTaskInput.model_validate_json(task_content)
    docker_container = DockerContainer(task.docker_image)
    sandbox = SandboxExecutor()

    def clean_exit(signum: int, frame: Any) -> None:
        print("\nKill signal received, cleaning in progress...")
        docker_container.stop_and_remove()
        sandbox.close()
        sys.exit(143)

    signal.signal(signal.SIGTERM, clean_exit)
    signal.signal(signal.SIGINT, clean_exit)

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
        )
        agent.run()
    finally:
        sandbox.close()
        docker_container.stop_and_remove()


if __name__ == "__main__":
    main()
