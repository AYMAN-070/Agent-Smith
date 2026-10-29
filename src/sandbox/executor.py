"""Isolated code execution sandbox with security constraints and resource limits."""

from __future__ import annotations

import ast
import builtins
import io
import multiprocessing
import resource
import sys
import traceback
from collections.abc import Callable, Mapping, Sequence
from multiprocessing.queues import Queue
from pathlib import Path
from typing import Any, cast

from src.models import SandboxConfig

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
    """Signal that the executed code has returned its final answer."""

    def __init__(self, answer: Any) -> None:
        """Initialize exception with final answer payload."""
        super().__init__()
        self.answer = answer


def agent_final_answer(answer: Any) -> None:
    """Stop execution and pass the final answer to the worker."""
    raise FinalAnswerException(answer)


def create_safe_import(
    authorized_imports: Sequence[str],
) -> Callable[..., Any]:
    """Return an import function that allows only configured modules."""
    real_import = builtins.__import__

    def safe_import(
        name: str,
        globals: Mapping[str, Any] | None = None,
        locals: Mapping[str, Any] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> Any:
        """Validate module name against allowed patterns before importing."""
        allowed = any(
            name == module
            or (module.endswith(".*") and name.startswith(module[:-2] + "."))
            for module in authorized_imports
        )
        if not allowed:
            raise ImportError(
                f"Sandbox security: importing module '{name}' is forbidden."
            )

        return real_import(name, globals, locals, fromlist, level)

    return safe_import


def create_safe_open(
    allowed_directories: Sequence[str],
) -> Callable[..., Any]:
    """Return an open function restricted to configured directories."""
    real_open = builtins.open

    def safe_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        """Validate file path against allowed directories before opening."""
        if not isinstance(file, (str, Path)):
            raise PermissionError(
                "Sandbox security: only string and Path filenames are allowed."
            )

        target = Path(file).resolve()
        for directory in allowed_directories:
            allowed_path = Path(directory).resolve()
            try:
                target.relative_to(allowed_path)
            except ValueError:
                continue
            return real_open(target, *args, **kwargs)

        raise PermissionError(
            f"Sandbox security: access to '{target}' is denied. "
            f"Allowed directories: {list(allowed_directories)}"
        )

    return safe_open


def create_safe_environment(
    config: SandboxConfig,
    tools: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the globals dictionary used to execute code in the sandbox."""
    safe_builtins = SAFE_BUILTINS.copy()
    safe_builtins["__import__"] = create_safe_import(config.authorized_imports)
    safe_builtins["open"] = create_safe_open(config.allowed_directories)

    environment: dict[str, Any] = {
        "__builtins__": safe_builtins,
        "final_answer": agent_final_answer,
    }

    # Make callable tools (including MCP wrappers) available by name.
    for name, tool in (tools or {}).items():
        if callable(tool):
            environment[name] = tool

    return environment


def apply_network_block() -> None:
    """Disable all inbound and outbound network access in the worker process."""

    class BlockedSocket:
        """Dummy socket class that disallows all socket instantiations."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Raise PermissionError on socket creation."""
            raise PermissionError(
                "Sandbox security: network access is forbidden."
            )

    def blocked_func(*args: Any, **kwargs: Any) -> Any:
        """Raise PermissionError on blocked network operations."""
        raise PermissionError("Sandbox security: network access is forbidden.")

    import socket

    for attr in (
        "create_connection",
        "getaddrinfo",
        "gethostbyname",
        "gethostbyname_ex",
        "getnameinfo",
        "socketpair",
        "fromfd",
    ):
        setattr(socket, attr, blocked_func)
    socket.socket = BlockedSocket

    try:
        import _socket

        for attr in (
            "getaddrinfo",
            "gethostbyname",
            "gethostbyname_ex",
            "getnameinfo",
        ):
            setattr(_socket, attr, blocked_func)
        _socket.socket = BlockedSocket
    except (ImportError, AttributeError):
        pass


def apply_system_limits(config: SandboxConfig) -> None:
    """Limit the worker process's virtual memory and block network access."""
    memory_bytes = config.max_memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    apply_network_block()


def transform_to_interactive_code(code: str) -> Any:
    """Transform top-level unassigned tool calls to automatically print.

    Emulates an interactive REPL environment (IPython / Jupyter) so that
    unassigned tool calls (e.g. `run_tests()`, `read_file(...)`, etc.)
    automatically write their return value to stdout without requiring
    the LLM to explicitly wrap them in `print()`.

    Parameters
    ----------
    code : str
        Raw Python source code from the model.

    Returns
    -------
    Any
        Compiled code object ready for exec, or original code if parsing fails.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    for node in tree.body:
        # Wrap standalone top-level function/tool calls
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            func = node.value.func
            # Do not double-wrap if already print(...) or final_answer(...)
            if isinstance(func, ast.Name) and func.id in (
                "print",
                "final_answer",
            ):
                continue

            node.value = ast.Call(
                func=ast.Name(id="print", ctx=ast.Load()),
                args=[node.value],
                keywords=[],
            )

    ast.fix_missing_locations(tree)
    try:
        return compile(tree, "<sandbox>", "exec")
    except Exception:
        return code


def isolated_worker(
    code: str,
    config: SandboxConfig,
    queue: Queue[Any],
    tools: dict[str, Any] | None = None,
) -> None:
    """Execute code in a separate process and send its result through the queue."""
    output = io.StringIO()
    original_stdout = sys.stdout

    try:
        apply_system_limits(config)
        safe_env = create_safe_environment(config, tools)

        sys.stdout = output
        executable_code = transform_to_interactive_code(code)
        exec(executable_code, safe_env)

        result = {
            "status": "success",
            "output": output.getvalue(),
        }

    except FinalAnswerException as error:
        result = {
            "status": "final_answer",
            "answer": error.answer,
            "output": output.getvalue(),
        }
    except Exception as error:
        result = {
            "status": "error",
            "error": traceback.format_exc(),
            "error_type": type(error).__name__,
            "output": output.getvalue(),
        }
    finally:
        sys.stdout = original_stdout

    queue.put(result)


class SandboxExecutor:
    """Run Python code in a separate process with resource limits and timeout."""

    def __init__(self, config: SandboxConfig | None = None) -> None:
        """Initialize sandbox executor with optional configuration."""
        self.config = config if config is not None else SandboxConfig()
        self.tool_wrappers: dict[str, Any] = {}
        self.mcp_client: Any = None
        self.tools = self.get_tools_manual()

    def connect_mcp(
        self,
        stdio_cmd: str | None = None,
        server_url: str | None = None,
    ) -> None:
        """Connect to an MCP server and register its tools as local wrappers."""
        if server_url:
            from src.mcp.client import HttpMCPClient

            self.mcp_client = HttpMCPClient(server_url)

        elif stdio_cmd:
            from src.mcp.client import MCPClient

            self.mcp_client = MCPClient(stdio_cmd)

        if self.mcp_client:
            self.mcp_client.start()

        if getattr(self.mcp_client, "tools", None):
            from src.mcp.wrappers import create_tool_wrappers

            self.tool_wrappers = create_tool_wrappers(self.mcp_client)
            self.tools = self.get_tools_manual()

    def get_tools_manual(self) -> str:
        """Return documentation for the tools available in the sandbox."""
        from src.sandbox.manual import generate_tools_manual

        mcp_tools = getattr(self.mcp_client, "tools", None)
        return generate_tools_manual(mcp_tools)

    def close(self) -> None:
        """Stop the MCP client if one is connected."""
        if self.mcp_client:
            self.mcp_client.stop()
            self.mcp_client = None

    def execute(
        self,
        code: str,
        tools: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute code in a worker process and return its result."""
        # MCP wrappers and caller-provided tools are available in the worker.
        merged_tools = {**self.tool_wrappers, **(tools or {})}
        result_queue: Queue[Any] = multiprocessing.Queue()

        process = multiprocessing.Process(
            target=isolated_worker,
            args=(code, self.config, result_queue, merged_tools),
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

        if not result_queue.empty():
            return cast(dict[str, Any], result_queue.get())

        return {
            "status": "error",
            "error": "Unknown error: Process exited without returning data.",
        }
