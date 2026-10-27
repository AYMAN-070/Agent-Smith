"""Sandbox module according to Agent Smith architecture."""

from src.sandbox.cli import main as sandbox_cli
from src.sandbox.executor import (
    SAFE_BUILTINS,
    FinalAnswerException,
    SandboxExecutor,
    agent_final_answer,
    apply_system_limits,
    create_safe_environment,
    create_safe_import,
    create_safe_open,
    isolated_worker,
)
from src.sandbox.manual import generate_tools_manual

__all__ = [
    "SAFE_BUILTINS",
    "FinalAnswerException",
    "SandboxExecutor",
    "agent_final_answer",
    "apply_system_limits",
    "create_safe_environment",
    "create_safe_import",
    "create_safe_open",
    "generate_tools_manual",
    "isolated_worker",
    "sandbox_cli",
]
