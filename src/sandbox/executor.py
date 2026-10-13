import multiprocessing
from typing import Dict, Any, Optional
from models import SandboxConfig
from sandbox.worker import isolated_worker


def execute_with_timeout(
    code: str,
    config: SandboxConfig,
    custom_modules: Optional[Dict[str, Any]] = None
) -> dict:
    """Runs the worker process with a strict timeout"""
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=isolated_worker,
        # On ajoute custom_modules dans la boîte de matériel envoyée au worker
        args=(code, config, queue, custom_modules)
    )

    process.start()
    process.join(timeout=config.max_execution_time_seconds)

    if process.is_alive():
        process.terminate()
        process.join()
        return {"status": "error", "error": "Sandbox Security: Execution timeout exceeded."}

    if not queue.empty():
        return queue.get()

    return {"status": "error", "error": "Unknown error: Process exited without returning data."}