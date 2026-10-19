import os
import re
import subprocess
from pathlib import Path

from fastmcp import FastMCP

mcp = FastMCP("SWE MCP Server")
TESTBED_PATH = os.environ.get(
    "TESTBED_PATH", "/testbed" if Path("/testbed").exists() else "."
)


# File System Tools
@mcp.tool()
def read_file(filepath: str, start_line: int, end_line: int) -> str:
    """Read the content of a file with line numbers.
    The output format must be similar to cat -n:"""
    path = Path(filepath)
    if not path.is_absolute():
        path = Path(TESTBED_PATH) / path
    if not path.is_file():
        return f"Error: File '{filepath}' not found."

    output = ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for l_nb, line in enumerate(f, start=1):
                if l_nb > end_line:
                    break
                if start_line <= l_nb:
                    output += f"{l_nb}: {line}"
        return output
    except Exception as e:
        return f"Error reading file '{filepath}': {e}"


@mcp.tool()
def edit_file(filepath: str, old_str: str, new_str: str) -> str:
    """Replace an exact string in a file with a new string."""
    path = Path(filepath)
    if not path.is_absolute():
        path = Path(TESTBED_PATH) / path
    if not path.is_file():
        return f"Error: File '{filepath}' not found."

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = f.read()
    except Exception as e:
        return f"Error reading file '{filepath}': {e}"

    if old_str not in data:
        return f"Error: old_str not found in {filepath}."

    data = data.replace(old_str, new_str)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        return "FILE EDITED"
    except Exception as e:
        return f"Error writing file '{filepath}': {e}"


@mcp.tool()
def list_files(directory: str = ".", pattern: str = "*") -> str:
    """List files in a directory matching a given pattern."""
    path = Path(directory)
    if not path.is_absolute():
        path = Path(TESTBED_PATH) / path
    if not path.exists() or not path.is_dir():
        return f"Error: '{directory}' does not exist or is not a directory."
    if not pattern:
        pattern = "*"

    matched_files = []
    testbed_base = Path(TESTBED_PATH).resolve()
    for p in path.rglob(pattern):
        if not p.is_file() or ".git" in p.parts:
            continue
        try:
            matched_files.append(str(p.resolve().relative_to(testbed_base)))
        except ValueError:
            matched_files.append(str(p.resolve()))

    if not matched_files:
        return f"No files matching pattern '{pattern}' found in '{directory}'."
    return "\n".join(sorted(matched_files))


# Code Search Tools
@mcp.tool()
def search_code(pattern: str, file_pattern: str = "*") -> str:
    """Perform a grep-like search in the codebase."""
    root_path = Path(TESTBED_PATH).resolve()
    if not root_path.exists():
        return f"Error: Root directory '{root_path}' does not exist."

    if not file_pattern:
        file_pattern = "*"

    try:
        compiled_pattern = re.compile(pattern)
    except re.error as e:
        return f"Error: Invalid regular expression pattern '{pattern}': {e}"

    results = []
    for file_path in root_path.rglob(file_pattern):
        if not file_path.is_file() or ".git" in file_path.parts:
            continue

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line_nb, line in enumerate(f, start=1):
                    if compiled_pattern.search(line):
                        results.append(
                            f"{file_path.resolve()}:{line_nb} {line.rstrip()}"
                        )
        except (PermissionError, OSError):
            continue

    if not results:
        return "No matches found."

    return "\n".join(results)


@mcp.tool()
def search_function_or_class_definition_in_code(name: str) -> str:
    """Find the definition of a function or a class.
    The output format must be similar to search_code format."""
    root_path = Path(TESTBED_PATH).resolve()
    if not root_path.exists():
        return f"Error: Root directory '{root_path}' does not exist."

    pattern = rf"^\s*(?:async\s+def|def|class)\s+{re.escape(name)}\b"
    try:
        compiled_pattern = re.compile(pattern)
    except re.error as e:
        return f"Error: Invalid pattern for name '{name}': {e}"

    results = []
    for file_path in root_path.rglob("*.py"):
        if not file_path.is_file() or ".git" in file_path.parts:
            continue

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line_nb, line in enumerate(f, start=1):
                    if compiled_pattern.search(line):
                        results.append(
                            f"{file_path.resolve()}:{line_nb} {line.rstrip()}"
                        )
        except (PermissionError, OSError):
            continue

    if not results:
        return "No matches found."

    return "\n".join(results)


@mcp.tool()
def find_references(name: str, filepath: str, line: int) -> str:
    """Find all usages of a symbol (function or class).
    The output format must be similar to search_code format."""
    root_path = Path(TESTBED_PATH).resolve()
    if not root_path.exists():
        return f"Error: Root directory '{root_path}' does not exist."

    pattern = rf"\b{re.escape(name)}\b"
    try:
        compiled_pattern = re.compile(pattern)
    except re.error as e:
        return f"Error: Invalid pattern for name '{name}': {e}"

    def_path = None
    try:
        p = Path(filepath)
        def_path = (p if p.is_absolute() else (root_path / p)).resolve()
    except Exception:
        pass

    try:
        target_line = int(line)
    except (ValueError, TypeError):
        target_line = -1

    results = []
    for file_path in root_path.rglob("*.py"):
        if not file_path.is_file() or ".git" in file_path.parts:
            continue

        resolved_file = file_path.resolve()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line_nb, line_content in enumerate(f, start=1):
                    if (
                        def_path
                        and resolved_file == def_path
                        and line_nb == target_line
                    ):
                        continue
                    if compiled_pattern.search(line_content):
                        results.append(
                            f"{resolved_file}:{line_nb} {line_content.rstrip()}"
                        )
        except (PermissionError, OSError):
            continue

    if not results:
        return "No matches found."

    return "\n".join(results)


# Execution Tools
@mcp.tool()
def run_tests() -> str:
    """Execute the evaluation script."""
    eval_path = os.environ.get("EVAL_SCRIPT_PATH", "/eval.sh")
    script = Path(eval_path)
    if not script.is_file():
        script = Path(TESTBED_PATH) / "eval.sh"
    if not script.is_file():
        return f"Error: Evaluation script '{eval_path}' not found."
    try:
        res = subprocess.run(
            ["/bin/bash", str(script)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=TESTBED_PATH,
        )
        return (
            f"Exit code: {res.returncode}\n"
            f"--- STDOUT ---\n{res.stdout}\n"
            f"--- STDERR ---\n{res.stderr}"
        )
    except subprocess.TimeoutExpired:
        return "Error: Test execution timed out (exceeded 300s)."
    except Exception as e:
        return f"Error executing tests: {e}"


@mcp.tool()
def get_patch() -> str:
    """Retrieve the unified git diff of all changes made to the repository, depending on
    the implementation."""
    root_path = Path(TESTBED_PATH).resolve()
    if not root_path.exists():
        return f"Error: Root directory '{root_path}' does not exist."

    try:
        res = subprocess.run(
            ["git", "-c", "core.fileMode=false", "diff"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(root_path),
        )
        if res.returncode != 0:
            return f"Error generating patch (exit code {res.returncode}): {res.stderr}"
        return res.stdout
    except subprocess.TimeoutExpired:
        return "Error: git diff timed out (exceeded 30s)."
    except Exception as e:
        return f"Error executing git diff: {e}"


@mcp.tool()
def run_command(command: str, workdir: str = "") -> str:
    """Execute a shell command in the specified working directory.
    Returns the command’s stdout, stderr, and exit code."""
    if not workdir:
        cwd = Path(TESTBED_PATH)
    else:
        cwd = Path(workdir)
        if not cwd.is_absolute():
            cwd = Path(TESTBED_PATH) / cwd

    if not cwd.exists() or not cwd.is_dir():
        return f"Error: Working directory '{cwd}' does not exist or is not a directory."

    try:
        res = subprocess.run(
            command,
            shell=True,
            executable="/bin/bash",
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(cwd),
        )
        return (
            f"Exit code: {res.returncode}\n"
            f"--- STDOUT ---\n{res.stdout}\n"
            f"--- STDERR ---\n{res.stderr}"
        )
    except subprocess.TimeoutExpired:
        return f"Error: Command '{command}' timed out (exceeded 120s)."
    except Exception as e:
        return f"Error running command: {e}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SWE-bench MCP Server")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
        help="MCP transport protocol",
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port for HTTP/SSE transport"
    )
    args, _ = parser.parse_known_args()

    if args.transport in ("sse", "streamable-http"):
        mcp.run(transport=args.transport, port=args.port)
    else:
        mcp.run(transport="stdio")
