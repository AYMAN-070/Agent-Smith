import argparse
import json
import sys
from typing import Any, Dict, Optional
from src.models import SandboxConfig
from src.sandbox.executor import SandboxExecutor
from src.sandbox.guards import create_safe_environment, FinalAnswerException
import io


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


def load_config(config_path: Optional[str]) -> SandboxConfig:
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


def run_interactive_repl(
    executor: SandboxExecutor,
    custom_modules: Optional[Dict[str, Any]] = None,
) -> None:
    """Runs the Read-Eval-Print Loop (REPL)
    for the sandbox in a persistent safe namespace."""

    print("=== Agent Smith Interactive Sandbox ===")
    print("Type 'exit' or use Ctrl+D to quit.")

    # Create one persistent safe namespace for the entire REPL session
    merged_modules = {**executor.custom_modules}
    if custom_modules:
        merged_modules.update(custom_modules)
    repl_env = create_safe_environment(
        executor.config, custom_modules=merged_modules
    )

    # Inject tool functions directly into
    #  repl_env so they are accessible as global functions
    if custom_modules:
        for k, v in custom_modules.items():
            if callable(v):
                repl_env[k] = v
            elif isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if callable(sub_v):
                        repl_env[sub_k] = sub_v

    while True:
        try:
            user_code = input("sandbox>>> ")

            if user_code.strip() == "exit":
                break
            if not user_code.strip():
                continue

            captured_stdout = io.StringIO()
            old_stdout = sys.stdout
            try:
                sys.stdout = captured_stdout
                exec(user_code, repl_env)
            except FinalAnswerException as fa:
                sys.stdout = old_stdout
                print(f"final_answer captured: {fa.answer}")
            except Exception as e:
                sys.stdout = old_stdout
                print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
            else:
                sys.stdout = old_stdout
                out = captured_stdout.getvalue()
                if out:
                    print(out, end="" if out.endswith("\n") else "\n")
            finally:
                sys.stdout = old_stdout

        except EOFError:
            print("\nExiting sandbox.")
            break
        except KeyboardInterrupt:
            print(
                "\nKeyboardInterrupt (Ctrl+C). Type 'exit' or Ctrl+D to quit."
            )


def main() -> None:
    args = parse_arguments()
    config = load_config(args.config_file)
    executor = SandboxExecutor(config=config)

    mcp_client = None
    custom_modules: dict = {}

    if args.mcp_stdio:
        from src.mcp.client import MCPClient
        from src.mcp.wrappers import create_tool_wrappers

        try:
            mcp_client = MCPClient(args.mcp_stdio)
            mcp_client.start()
            tool_wrappers = create_tool_wrappers(mcp_client)
            custom_modules["agent_tools"] = tool_wrappers
            # Also inject tools directly so they
            #  can be called as functions without import
            custom_modules.update(tool_wrappers)
            print(
                f"Connected to MCP server via stdio."
                f" Tools: {list(tool_wrappers.keys())}"
            )
        except Exception as e:
            print(
                f"Error connecting to MCP server (stdio): {e}", file=sys.stderr
            )
            sys.exit(1)

    elif args.mcp_server:
        from src.mcp.client import HttpMCPClient
        from src.mcp.wrappers import create_tool_wrappers

        try:
            mcp_client = HttpMCPClient(args.mcp_server)
            mcp_client.start()
            tool_wrappers = create_tool_wrappers(mcp_client)
            custom_modules["agent_tools"] = tool_wrappers
            custom_modules.update(tool_wrappers)
            print(
                f"Connected to MCP server via HTTP ({args.mcp_server})."
                " Tools: {list(tool_wrappers.keys())}"
            )
        except Exception as e:
            print(
                f"Error connecting to MCP server (HTTP): {e}", file=sys.stderr
            )
            sys.exit(1)

    try:
        run_interactive_repl(executor, custom_modules=custom_modules)
    finally:
        if mcp_client:
            mcp_client.stop()


if __name__ == "__main__":
    main()
