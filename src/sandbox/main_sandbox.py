import argparse
import json
import sys
from typing import Dict, Any
from models import SandboxConfig
from sandbox.executor import execute_with_timeout


def parse_arguments():
    """Parses command line arguments for the Sandbox CLI."""
    parser = argparse.ArgumentParser(description="Agent Smith Sandbox CLI")

    # Optional positional argument for the JSON config
    parser.add_argument(
        "config_file",
        nargs="?",
        help="Path to JSON configuration file (e.g., sandbox_template.json)"
    )

    parser.add_argument(
        "--mcp-stdio",
        type=str,
        help="Command to launch MCP server via stdio "
    )

    parser.add_argument(
        "--mcp-server",
        type=str,
        help="URL for HTTP MCP server"
    )

    return parser.parse_args()


def load_config(config_path: str | None) -> SandboxConfig:
    """Loads configuration from a JSON file if provided via CLI."""
    if config_path and config_path.endswith('.json'):
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return SandboxConfig(**config_data)
        except Exception as e:
            print(f"Error loading config file: {e}")
            sys.exit(1)
    return SandboxConfig()


def run_interactive_repl(config: SandboxConfig,
                         custom_modules: Dict[str, Any] = None) -> None:
    """Runs the Read-Eval-Print Loop for the sandbox."""
    print("=== Agent Smith Interactive Sandbox ===")
    print("Type 'exit' or use Ctrl+D to quit.")

    while True:
        try:
            user_code = input("sandbox>>> ")

            if user_code.strip() == "exit":
                break
            if not user_code.strip():
                continue
            result = execute_with_timeout(user_code, config, custom_modules)

            if result.get("status") == "success":
                print(result.get("output", ""))
            else:
                print(f"Error: {result.get('error')}")

        except EOFError:
            print("\nExiting sandbox.")
            break
        except KeyboardInterrupt:
            print("\nInterrupt (Ctrl+C). Type 'exit' or Ctrl+D to quit.")


def mock_read_file(filepath: str) -> str:
    """A mock tool to simulate reading a file."""
    return f"Simulated content of {filepath}"


if __name__ == "__main__":
    args = parse_arguments()
    config = load_config(args.config_file)

    my_custom_modules = {
        "agent_tools": {
            "read_file": mock_read_file
        }
    }
    run_interactive_repl(config, my_custom_modules)
