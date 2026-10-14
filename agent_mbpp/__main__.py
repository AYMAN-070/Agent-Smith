import argparse
from pathlib import Path

from src.agent.loop import Loop
from src.models import MBPPTaskInput


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI")
    parser.add_argument(
        "--task-file", type=str, required=True, help="path to task.json"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="solution.json",
        help="path to solution.json output",
    )
    args = parser.parse_args()
    task_content = Path(args.task_file).read_text(encoding="utf-8")
    task = MBPPTaskInput.model_validate_json(task_content)
    result = Loop(task)
    print(result.loop())


if __name__ == "__main__":
    main()
