import json
import os
import sys
from src.sandbox.executor import SandboxExecutor
from src.agent.loop import SWEAgentLoop
from src.mcp.client import MCPClient


def load_issue(filepath: str) -> str:
    """LOad bug description from JSON file"""
    if not os.path.exists(filepath):
        print(f"Error: Could not find {filepath}")
        sys.exit(1)

    with open(filepath, 'r') as f:
        data = json.load(f)
        return data.get("problem_statement", "No description provided.")


def main():
    print("===" * 15)
    print("🤖 STARTING SWE-BENCH AGENT")
    print("===" * 15)

    current_dir = os.path.dirname(__file__)
    task_path = os.path.join(current_dir, "..", "task.json")
    issue_description = load_issue(task_path)

    server_script_path = os.path.join(current_dir, "..", "mcp_swe_server.py")
    mcp_client = MCPClient(server_script_path)
    mcp_client.start()

    mcp_tools = mcp_client.get_wrapped_tools()

    sandbox = SandboxExecutor()
    sandbox.register_custom_module("agent_tools", mcp_tools)

    agent_loop = SWEAgentLoop(
        issue_description=issue_description,
        sandbox=sandbox
    )
    result = agent_loop.run()

    mcp_client.stop()
    print("\n🏁 FINAL RESULT:", result)


if __name__ == "__main__":
    main()
