import builtins
import io
import multiprocessing
from multiprocessing.queues import Queue
import resource
import sys
import traceback
import types
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Dict, Optional

from src.models import SandboxConfig

#  SECURITY & GUARDS (Safe Builtins, Imports, and Final Answer)

SAFE_BUILTINS: dict[str, Any] = {
    "print": print,
    "len": len,
    "range": range,
    "int": int,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "float": float,
    "tuple": tuple,
    "set": set,
    "frozenset": frozenset,
    "bytes": bytes,
    "complex": complex,
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "round": round,
    "divmod": divmod,
    "pow": pow,
    "enumerate": enumerate,
    "zip": zip,
    "reversed": reversed,
    "sorted": sorted,
    "filter": filter,
    "map": map,
    "any": any,
    "all": all,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "type": type,
    "callable": callable,
    "hash": hash,
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "AttributeError": AttributeError,
    "NotImplementedError": NotImplementedError,
    "StopIteration": StopIteration,
    "AssertionError": AssertionError,
}


class FinalAnswerException(Exception):
    """Exception raised when the agent calls final_answer()."""

    def __init__(self, answer: Any) -> None:
        super().__init__()
        self.answer = answer


def agent_final_answer(answer: Any) -> None:
    """Builtin function injected into sandbox to capture final answer."""
    raise FinalAnswerException(answer)


ModuleMapping = Mapping[str, types.ModuleType | Mapping[str, Any]]


def create_safe_import(
    authorized_imports: Sequence[str],
    custom_modules: ModuleMapping | None = None,
) -> Callable[..., Any]:
    """Create a guarded __import__ function that respects allowed imports."""
    real_import = builtins.__import__
    resolved_custom_modules: ModuleMapping = (
        custom_modules if custom_modules is not None else {}
    )

    def safe_import(
        name: str,
        globals: Mapping[str, Any] | None = None,
        locals: Mapping[str, Any] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> Any:
        #  Check if a custom or mocked module is provided
        if name in resolved_custom_modules:
            mod = resolved_custom_modules[name]
            if isinstance(mod, Mapping):
                fake_module = types.ModuleType(name)
                for attr, val in mod.items():
                    setattr(fake_module, attr, val)
                return fake_module
            return mod

        #  Check for allowed module imports
        is_allowed = False
        if name in authorized_imports:
            is_allowed = True
        else:
            for allowed in authorized_imports:
                if allowed.endswith(".*"):
                    base_module = allowed[:-2]
                    if name.startswith(base_module + "."):
                        is_allowed = True
                        break

        if not is_allowed:
            raise ImportError(
                f"Sandbox security: importing module '{name}' is forbidden."
            )

        return real_import(name, globals, locals, fromlist, level)

    return safe_import


def create_safe_environment(
    config: SandboxConfig,
    custom_modules: Any | None = None,
) -> dict[str, Any]:
    """Create a restricted execution environment
    with safe builtins and imports."""
    builtins_dict = dict(SAFE_BUILTINS)
    builtins_dict["__import__"] = create_safe_import(
        config.authorized_imports, custom_modules=custom_modules
    )

    env: dict[str, Any] = {
        "__builtins__": builtins_dict,
        "final_answer": agent_final_answer,
    }

    if custom_modules:
        for k, v in custom_modules.items():
            if callable(v):
                env[k] = v
            elif isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if callable(sub_v):
                        env[sub_k] = sub_v

    return env


#  ISOLATED WORKER & RESOURCE LIMITS


def apply_system_limits(config: SandboxConfig) -> None:
    """Apply memory limit to the current process via resource.setrlimit."""
    byte_limit = config.max_memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (byte_limit, byte_limit))


def isolated_worker(
    code: str,
    config: SandboxConfig,
    queue: Queue,
    custom_modules: dict[str, Any] | None = None,
    env: dict[str, Any] | None = None,
) -> None:
    """Executes code in an isolated process,
    enforces limits, and returns results."""
    captured_output = io.StringIO()
    try:
        apply_system_limits(config)
        safe_env = create_safe_environment(
            config,
            custom_modules=custom_modules,
        )
        if env:
            safe_env.update(env)

        sys.stdout = captured_output
        exec(code, safe_env)
        sys.stdout = sys.__stdout__

        import pickle

        updated_env: dict[str, Any] = {}
        for k, v in safe_env.items():
            if k.startswith("__") or k == "final_answer":
                continue
            if custom_modules and (k in custom_modules or k == "agent_tools"):
                continue
            try:
                pickle.dumps(v)
                updated_env[k] = v
            except Exception:
                pass

        queue.put(
            {
                "status": "success",
                "output": captured_output.getvalue(),
                "env": updated_env,
            }
        )

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


# SANDBOX EXECUTOR (Supervisor with Process & Timeout)


class SandboxExecutor:
    """Manages code execution inside an isolated
    worker process with strict timeout."""

    def __init__(self, config: Optional[SandboxConfig] = None) -> None:
        self.config: SandboxConfig = (
            config if config is not None else SandboxConfig()
        )
        self.custom_modules: Dict[str, Any] = {}
        self.mcp_client: Any = None
        self.tools: str = self.get_tools_manual()

    def connect_mcp(
        self,
        stdio_cmd: Optional[str] = None,
        server_url: Optional[str] = None,
    ) -> None:
        """Connects to an MCP server (stdio or HTTP) and registers tools in sandbox."""
        if server_url:
            from src.mcp.client import HttpMCPClient

            self.mcp_client = HttpMCPClient(server_url)
            self.mcp_client.start()
        elif stdio_cmd:
            from src.mcp.client import MCPClient

            self.mcp_client = MCPClient(stdio_cmd)
            self.mcp_client.start()

        if self.mcp_client and getattr(self.mcp_client, "tools", None):
            from src.mcp.wrappers import create_tool_wrappers

            tool_wrappers = create_tool_wrappers(self.mcp_client)
            self.register_custom_module("agent_tools", tool_wrappers)
            self.custom_modules.update(tool_wrappers)
            self.tools = self.get_tools_manual()

    def get_tools_manual(self) -> str:
        """Returns the documentation manual for all tools available in the sandbox."""
        from src.sandbox.manual import generate_tools_manual

        tools = (
            self.mcp_client.tools
            if self.mcp_client and getattr(self.mcp_client, "tools", None)
            else None
        )
        return generate_tools_manual(tools)

    def close(self) -> None:
        """Terminates connected MCP server client cleanly if running."""
        if self.mcp_client:
            self.mcp_client.stop()
            self.mcp_client = None

    def register_custom_module(self, name: str, module_or_tools: Any) -> None:
        """Register custom module or mock tools for the sandbox."""
        self.custom_modules[name] = module_or_tools

    def execute(
        self,
        code: str,
        custom_modules: Optional[Dict[str, Any]] = None,
        env: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Runs the worker process with strict timeout and isolation."""
        merged_modules: Dict[str, Any] = {**self.custom_modules}
        if custom_modules:
            merged_modules.update(custom_modules)

        queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=isolated_worker,
            args=(code, self.config, queue, merged_modules, env),
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
