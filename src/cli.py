"""Command-line argument parser helper for agents."""

import argparse


class AgentArgs:
    """Parses and stores common CLI arguments for agent runners."""

    def __init__(self, description: str) -> None:
        """Initialize argument parser with the provided description."""
        parser = argparse.ArgumentParser(description=description)

        parser.add_argument(
            "--task-file", type=str, required=True, help="Path to task.json"
        )
        parser.add_argument(
            "--output",
            type=str,
            default="solution.json",
            help="Path to output solution.json",
        )

        parser.add_argument(
            "--model-name",
            type=str,
            default=None,
            help="Target LLM model name",
        )

        parser.add_argument(
            "--provider-url",
            type=str,
            default=None,
            help="Target provider API URL",
        )
        parsed = parser.parse_args()

        self.task_file: str = parsed.task_file
        self.output: str | None = parsed.output
        self.model_name: str | None = parsed.model_name
        self.provider_url: str | None = parsed.provider_url
