# ABOUTME: Top-level moulinette package for MBPP and SWE-bench evaluation.
# ABOUTME: Re-exports key classes and models for convenient imports.
import os
from pathlib import Path


def _init_docker_env() -> None:
    """Auto-detect Docker rootless socket on 42 school / unprivileged machines."""
    if "DOCKER_HOST" not in os.environ:
        try:
            uid = os.getuid()
            user_sock = Path(f"/run/user/{uid}/docker.sock")
            xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
            xdg_sock = Path(xdg_runtime) / "docker.sock" if xdg_runtime else None

            if user_sock.exists():
                os.environ["DOCKER_HOST"] = f"unix://{user_sock}"
            elif xdg_sock and xdg_sock.exists():
                os.environ["DOCKER_HOST"] = f"unix://{xdg_sock}"
        except Exception:
            pass


_init_docker_env()

from moulinette.models import (
    SandboxConfig,
    MBPPTaskInput,
    SWEBenchTaskInput,
    StepMetrics,
    SolutionOutput,
    MetricsLimits,
    MetricsValidationResult,
)
from moulinette.mbpp import InteractMBPP
from moulinette.swebench import InteractSweBench, Difficulty, SEED_POOL

__all__ = [
    "InteractMBPP",
    "InteractSweBench",
    "Difficulty",
    "SEED_POOL",
    "SandboxConfig",
    "MBPPTaskInput",
    "SWEBenchTaskInput",
    "StepMetrics",
    "SolutionOutput",
    "MetricsLimits",
    "MetricsValidationResult",
]
