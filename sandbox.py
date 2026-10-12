import builtins
import types
import resource
import multiprocessing
from multiprocessing.queues import Queue
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Union
from sandbox_config import SandboxConfig

ModuleMapping = Mapping[str, Union[types.ModuleType, Mapping[str, Any]]]


def create_safe_environment(
    config: 'SandboxConfig',
    custom_modules: Optional[Any] = None,
) -> Dict[str, Any]:

    safe_builtins: Dict[str, Any] = {
        'print': print,
        'len': len,
        'range': range,
        'int': int,
        'str': str,
        'bool': bool,
        'list': list,
        'dict': dict,
        'float': float,
        'tuple': tuple,
        'set': set,
        'frozenset': frozenset,
        'bytes': bytes,
        'complex': complex,

        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'round': round,
        'divmod': divmod,
        'pow': pow,
        'enumerate': enumerate,
        'zip': zip,
        'reversed': reversed,
        'sorted': sorted,
        'filter': filter,
        'map': map,
        'any': any,
        'all': all,

        'isinstance': isinstance,
        'issubclass': issubclass,
        'type': type,
        'callable': callable,
        'hash': hash,

        'Exception': Exception,
        'ValueError': ValueError,
        'TypeError': TypeError,
        'KeyError': KeyError,
        'IndexError': IndexError,
        'AttributeError': AttributeError,
        'NotImplementedError': NotImplementedError,
        'StopIteration': StopIteration,
        'AssertionError': AssertionError,
    }

    safe_builtins['__import__'] = create_safe_import(
        config.authorized_imports,
        custom_modules=custom_modules
    )

    return {
        '__builtins__': safe_builtins,
    }


def create_safe_import(
    authorized_imports: Sequence[str],
    custom_modules: Optional[ModuleMapping] = None,
) -> Callable[..., Any]:
    real_import = builtins.__import__
    if custom_modules is not None:
        resolved_custom_modules = custom_modules
    else:
        resolved_custom_modules = {}

    def safe_import(
        name: str,
        globals: Optional[Mapping[str, Any]] = None,
        locals: Optional[Mapping[str, Any]] = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> Any:
        # 1. Check if a custom or mocked module is provided
        if name in resolved_custom_modules:
            mod = resolved_custom_modules[name]
            # Convert a dictionary of functions or attributes into a
            # ModuleType if needed
            if isinstance(mod, Mapping):
                fake_module = types.ModuleType(name)
                for attr, val in mod.items():
                    setattr(fake_module, attr, val)
                return fake_module
            return mod

        # 2. Check for allowed module imports
        is_allowed = False
        if name in authorized_imports:
            is_allowed = True
        else:
            # Check for submodules (e.g. "math.*")
            for allowed in authorized_imports:
                if allowed.endswith('.*'):
                    base_module = allowed[:-2]  # Remove trailing ".*"
                    if name.startswith(base_module + "."):
                        is_allowed = True
                        break

        if not is_allowed:
            raise ImportError(f"Sandbox security: importing module '{name}' is forbidden.")

        # If allowed, execute the genuine import
        return real_import(name, globals, locals, fromlist, level)

    return safe_import


def apply_system_limits(config: SandboxConfig) -> None:
    byte_limit = config.max_memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (byte_limit, byte_limit))


def isolated_worker(
    code: str,
    config: SandboxConfig,
    result_queue: 'Queue[str]',
) -> None:
    try:
        apply_system_limits(config)
        safe_env = create_safe_environment(config)
        exec(code, safe_env)
        result_queue.put("Success")
    except Exception as e:
        result_queue.put(f"Error : {e}")


def execute_with_timeout(code: str, config: SandboxConfig) -> str:
    # A queue to retrieve the child process result
    queue: 'Queue[str]' = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=isolated_worker,
        args=(code, config, queue)
    )
    process.start()
    # Wait for the process to finish within the configured timeout
    process.join(timeout=config.max_execution_time_seconds)
    if process.is_alive():
        # Time is up, process is still alive: terminate it
        process.terminate()
        process.join()
        return "Sandbox Error : Timeout exceeded."
    if not queue.empty():
        return queue.get()
    return "Unknown error."
