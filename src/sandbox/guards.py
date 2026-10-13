import builtins
import types
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Union
from src.models import SandboxConfig

ModuleMapping = Mapping[str, Union[types.ModuleType, Mapping[str, Any]]]


def create_safe_environment(
    config: SandboxConfig,
    custom_modules: Optional[Any] = None,
) -> Dict[str, Any]:
    """Create a restricted execution with safe builtins and imports."""
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
    """Create a guarded __import__ function that respects allowed imports ."""
    real_import = builtins.__import__
    resolved_custom_modules: ModuleMapping = custom_modules if custom_modules is not None else {}

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
                    base_module = allowed[:-2]
                    if name.startswith(base_module + "."):
                        is_allowed = True
                        break

        if not is_allowed:
            raise ImportError(f"Sandbox security: importing module '{name}' is forbidden.")

        # If allowed, execute the genuine import
        return real_import(name, globals, locals, fromlist, level)

    return safe_import
