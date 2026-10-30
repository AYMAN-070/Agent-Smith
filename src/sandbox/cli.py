"""Interactive REPL command-line interface for the sandbox."""

import argparse
import json
import sys

from src.models import SandboxConfig
from src.sandbox.executor import SandboxExecutor


def parse_arguments() -> argparse.Namespace:
    """Parses command line arguments for
    the Sandbox CLI according to specification."""
    parser = argparse.ArgumentParser(description="Agent Smith Sandbox CLI")

    parser.add_argument(
        "config_file",
        nargs="?",
        help="Path to JSON configuration file (e.g., sandbox_template.json)",
    )

    parser.add_argument(
        "--mcp-stdio",
        type=str,
        help="Command to launch MCP server via stdio",
    )

    parser.add_argument(
        "--mcp-server",
        type=str,
        help="URL for HTTP MCP server",
    )

    return parser.parse_args()


def load_config(config_path: str | None) -> SandboxConfig:
    """Loads SandboxConfig from a JSON file if
    provided, otherwise returns default config."""
    if config_path:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            return SandboxConfig.model_validate(config_data)
        except Exception as e:
            print(
                f"Error loading configuration file '{config_path}': {e}",
                file=sys.stderr,
            )
            sys.exit(1)
    return SandboxConfig()


def run_interactive_repl(executor: SandboxExecutor) -> None:
    """Runs the Read-Eval-Print Loop (REPL) for the sandbox in an isolated worker process."""

    print("=== Agent Smith Interactive Sandbox ===")
    print("Type 'exit' or use Ctrl+D to quit.")

    code_preamble: list[str] = []

    while True:
        try:
            user_code = input("sandbox>>> ")

            if user_code.strip() == "exit":
                break
            if not user_code.strip():
                continue

            # Prepend accumulated function/class definitions if any
            full_code = (
                "\n".join(code_preamble + [user_code])
                if code_preamble
                else user_code
            )

            result = executor.execute(full_code)

            status = result.get("status")
            if status == "final_answer":
                print(f"final_answer captured: {result.get('answer')}")
            elif status == "error":
                raw_error = result.get('error', '').strip()
                error_line = raw_error.splitlines()[-1] if raw_error else "Unknown execution error"
                print(f"Error: {error_line}", file=sys.stderr)
                partial = result.get("output", "")
                if partial:
                    print(partial, end="" if partial.endswith("\n") else "\n")

            else:
                out = result.get("output", "")
                if out:
                    print(out, end="" if out.endswith("\n") else "\n")

                # If user defined a function or class, retain in preamble
                stripped = user_code.strip()
                if stripped.startswith(("def ", "class ")):
                    code_preamble.append(user_code)

        except (EOFError, SystemExit):
            print("\nExiting sandbox.")
            break
        except KeyboardInterrupt:
            print(
                "\nKeyboardInterrupt (Ctrl+C). Type 'exit' or Ctrl+D to quit."
            )


def main() -> None:
    """Entry point for the sandbox CLI."""
    args = parse_arguments()
    config = load_config(args.config_file)

    executor = SandboxExecutor(config=config)

    try:
        executor.connect_mcp(
            stdio_cmd=args.mcp_stdio, server_url=args.mcp_server
        )
        if executor.mcp_client:
            tools_list = list(executor.tool_wrappers.keys())
            transport_info = (
                f"HTTP ({args.mcp_server})" if args.mcp_server else "stdio"
            )
            print(
                f"Connected to MCP server via {transport_info}."
                f" Tools: {tools_list}"
            )
    except Exception as e:
        print(f"Error connecting to MCP server: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if not sys.stdin.isatty():
            code = sys.stdin.read()
            if code.strip():
                result = executor.execute(code)
                status = result.get("status")
                out = result.get("output", "")
                if out:
                    print(out, end="" if out.endswith("\n") else "\n")
                if status == "final_answer":
                    print(f"final_answer captured: {result.get('answer')}")
                elif status == "error":
                    raw_error = result.get("error", "").strip()
                    error_line = (
                        raw_error.splitlines()[-1]
                        if raw_error
                        else "Unknown execution error"
                    )
                    print(f"Error: {error_line}", file=sys.stderr)
        else:
            run_interactive_repl(executor)
    finally:
        executor.close()


if __name__ == "__main__":
    main()
