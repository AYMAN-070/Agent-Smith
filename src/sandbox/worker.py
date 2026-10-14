import io
import resource
import sys
from multiprocessing.queues import Queue
from typing import Any

from src.models import SandboxConfig
from src.sandbox.guards import create_safe_environment


def apply_system_limits(config: SandboxConfig) -> None:
    """Apply memory limit to the current process via resource.setrlimit."""
    byte_limit = config.max_memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (byte_limit, byte_limit))


def isolated_worker(
    code: str,
    config: SandboxConfig,
    queue: Queue,
    custom_modules: dict[str, Any] | None = None,
) -> None:
    """Executes the code in an isolated environment and captures output."""
    try:
        apply_system_limits(config)
        safe_env = create_safe_environment(config, custom_modules)
        captured_output = io.StringIO()
        sys.stdout = captured_output

        exec(code, safe_env)

        sys.stdout = sys.__stdout__

        queue.put({"status": "success", "output": captured_output.getvalue()})

    except FinalAnswerException as fa_exc:
        sys.stdout = sys.__stdout__
        queue.put({
            "status": "final_answer",
            "answer": fa_exc.answer,
            "output": captured_output.getvalue()
        })
    except Exception as e:
        sys.stdout = sys.__stdout__
        queue.put({"status": "error", "error": f"{type(e).__name__}: {e!s}"})
