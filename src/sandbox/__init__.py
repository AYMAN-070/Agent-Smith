"""Sandbox module according to Agent Smith architecture."""

from src.sandbox.executor import (
    FinalAnswerException,
    SAFE_BUILTINS,
    SandboxExecutor,
    agent_final_answer,
    apply_system_limits,
    create_safe_environment,
    create_safe_import,
    isolated_worker,
)
from src.sandbox.manual import generate_tools_manual
from src.sandbox.cli import main as sandbox_cli

__all__ = [
    "FinalAnswerException",
    "SAFE_BUILTINS",
    "SandboxExecutor",
    "agent_final_answer",
    "apply_system_limits",
    "create_safe_environment",
    "create_safe_import",
    "isolated_worker",
    "generate_tools_manual",
    "sandbox_cli",
]
