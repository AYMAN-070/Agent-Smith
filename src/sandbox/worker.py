import io
import resource
import sys
from multiprocessing.queues import Queue
from typing import Any
import traceback

from src.models import SandboxConfig
from src.sandbox.guards import FinalAnswerException, create_safe_environment


def apply_system_limits(config: SandboxConfig) -> None:
    """Apply memory limit to the current process via resource.setrlimit."""
    byte_limit = config.max_memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (byte_limit, byte_limit))


def isolated_worker(
    code: str,
    config: SandboxConfig,
    queue: Queue,
    custom_modules: dict[str, Any] | None = None,
    initial_namespace: dict[str, Any] | None = None,
) -> None:
    """Executes the code in an isolated environment, captures output and updated namespace."""
    try:
        apply_system_limits(config)
        safe_env = create_safe_environment(
            config,
            custom_modules=custom_modules,
            initial_namespace=initial_namespace,
        )
        captured_output = io.StringIO()
        sys.stdout = captured_output

        exec(code, safe_env)

        sys.stdout = sys.__stdout__

        # Extract user variables defined during execution (ignore builtins and special keys)
        updated_namespace: dict[str, Any] = {}
        for k, v in safe_env.items():
            if k not in ("__builtins__", "final_answer"):
                try:
                    # Quick check to ensure the object can be pickled across multiprocessing queue
                    import pickle
                    pickle.dumps(v)
                    updated_namespace[k] = v
                except Exception:
                    pass

        queue.put({
            "status": "success",
            "output": captured_output.getvalue(),
            "namespace": updated_namespace,
        })

    except FinalAnswerException as fa_exc:
        sys.stdout = sys.__stdout__
        queue.put(
            {
                "status": "final_answer",
                "answer": fa_exc.answer,
                "output": captured_output.getvalue(),
            }
        )
    except Exception as e:
        sys.stdout = sys.__stdout__
        tb_str = traceback.format_exc()
        queue.put(
            {
                "status": "error",
                "error": tb_str,
                "error_type": type(e).__name__,
                "output": captured_output.getvalue(),
            }
        )
