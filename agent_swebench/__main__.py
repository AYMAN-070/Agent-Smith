import argparse
import os
from pathlib import Path
from src.cli import AgentArgs

from src.agent.loop import SWEAgentLoop
from src.mcp.client import MCPClient
from src.models import SWEBenchTaskInput
from src.sandbox.executor import SandboxExecutor
from src.llm.llm import LlmRequest


def main():
    parser = AgentArgs("Agent SWE")
    task_content = Path(parser.task_file).read_text(encoding="utf-8")

    current_dir = os.path.dirname(__file__)
    server_script_path = os.path.join(current_dir, "..", "mcp_swe_server.py")
    mcp_client = MCPClient(server_script_path)
    mcp_client.start()
    llm_request = LlmRequest(parser.model_name, parser.provider_url)

    task = SWEBenchTaskInput.model_validate_json(task_content)

    sandbox = SandboxExecutor()

    agent_loop = SWEAgentLoop(task, sandbox, llm)

    result = agent_loop.run()

    finally:
        if mcp_client:
            mcp_client.stop()


if __name__ == "__main__":
    main()
