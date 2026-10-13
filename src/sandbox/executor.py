import multiprocessing
from typing import Dict, Any, Optional
from src.models import SandboxConfig
from src.sandbox.worker import isolated_worker


class SandboxExecutor:
    """Manages code execution inside an isolated worker process with resource limits and timeout."""

    def __init__(self, config: Optional[SandboxConfig] = None) -> None:
        self.config: SandboxConfig = config if config is not None else SandboxConfig()
        self.custom_modules: Dict[str, Any] = {}

    def register_custom_module(self, name: str, module_or_tools: Any) -> None:
        """Register custom module or mock tools for the sandbox."""
        self.custom_modules[name] = module_or_tools

    def execute(
        self,
        code: str,
        custom_modules: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Runs the worker process with strict timeout and isolation."""
        merged_modules: Dict[str, Any] = {**self.custom_modules}
        if custom_modules:
            merged_modules.update(custom_modules)

        queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=isolated_worker,
            args=(code, self.config, queue, merged_modules),
        )

        process.start()
        process.join(timeout=self.config.max_execution_time_seconds)

        if process.is_alive():
            process.terminate()
            process.join()
            return {
                "status": "error",
                "error": "Sandbox Security: Execution timeout exceeded.",
            }

        if not queue.empty():
            return queue.get()

        return {
            "status": "error",
            "error": "Unknown error: Process exited without returning data.",
        }


def execute_with_timeout(
    code: str,
    config: SandboxConfig,
    custom_modules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Functional wrapper for backwards compatibility."""
    executor = SandboxExecutor(config=config)
    return executor.execute(code, custom_modules=custom_modules)
