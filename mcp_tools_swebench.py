"""FastMCP server exposing SWE-bench development and testing tools."""

import os
import re
import subprocess
from pathlib import Path

from fastmcp import FastMCP

mcp = FastMCP("SWE MCP Server")

# Docker container ID for SWE-bench (if running against a container)
CONTAINER_ID = os.environ.get("SWE_CONTAINER_ID") or os.environ.get(
    "DOCKER_CONTAINER_ID"
)

# Host fallback repository root (used when running in isolation without Docker)
TESTBED_PATH = os.environ.get(
    "TESTBED_PATH", "/testbed" if Path("/testbed").exists() else "."
)


def _docker_exec(
    cmd: list[str],
    workdir: str = "/testbed",
    input_text: str | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    """Execute a command inside the active Docker container."""
    full_cmd = ["docker", "exec"]
    if input_text is not None:
        full_cmd.append("-i")
    if workdir:
        full_cmd.extend(["-w", workdir])
    full_cmd.append(CONTAINER_ID or "")
    full_cmd.extend(cmd)
    return subprocess.run(
        full_cmd,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@mcp.resource("swebench://guidelines")
def get_swebench_guidelines() -> str:
    """Return instructions and guidelines for solving SWE-bench tasks."""
    return (
        "# SWE-bench Guidelines\n\n"
        "### 1. Goal\n"
        "Solve real-world GitHub issues by creating a clean git patch.\n\n"
        "### 2. Workflow\n"
        "1. Search codebase using `search_code` and `list_files`.\n"
        "2. Read relevant files with `read_file`.\n"
        "3. Reproduce the bug using `run_tests` or `run_command`.\n"
        "4. Fix the bug with `edit_file` or `write_file`.\n"
        "5. Verify fix and check for regressions.\n"
        "6. Call `final_answer(get_patch())` to finish.\n"
    )


@mcp.prompt()
def debug_swebench_issue(issue_description: str) -> str:
    """Template prompt to guide reproducing and fixing a SWE-bench issue."""
    return (
        f"You are tasked with fixing the following issue:\n\n{issue_description}\n\n"
        "Follow these steps:\n"
        "1. Locate relevant code files.\n"
        "2. Reproduce the issue with tests.\n"
        "3. Edit files to fix the bug.\n"
        "4. Verify the fix and submit using final_answer(get_patch())."
    )


# File System Tools
@mcp.tool()
def read_file(filepath: str, start_line: int, end_line: int) -> str:
    """Read a file range with 1-indexed line numbers.

    Parameters:
      - filepath: Relative path from repository root.
      - start_line: First line to read (1-indexed).
      - end_line: Last line to read (inclusive).
    Note: Line numbers in output are for reading only.
    Do NOT include line numbers when editing with edit_file.
    """
    if CONTAINER_ID:
        target_path = Path(filepath)
        if not target_path.is_absolute():
            target_path = Path("/testbed") / target_path
        try:
            res = _docker_exec(["cat", str(target_path)])
            if res.returncode != 0:
                return f"Error: File '{filepath}' not found."
            lines = res.stdout.splitlines(keepends=True)
            output = ""
            for l_nb, line in enumerate(lines, start=1):
                if l_nb > end_line:
                    break
                if start_line <= l_nb:
                    output += f"{l_nb}: {line}"
            return output
        except subprocess.TimeoutExpired:
            return f"Error: Reading file '{filepath}' timed out."
        except Exception as e:
            return f"Error reading file '{filepath}': {e}"

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
    """Replace an exact unique code block in a file with new code.

    Parameters:
      - filepath: Relative path from repository root.
      - old_str: Exact matching string to replace. Must preserve exact
        whitespace and indentation, without line numbers.
      - new_str: New replacement string to insert.
    """
    if CONTAINER_ID:
        target_path = Path(filepath)
        if not target_path.is_absolute():
            target_path = Path("/testbed") / target_path
        try:
            res = _docker_exec(["cat", str(target_path)])
            if res.returncode != 0:
                return f"Error: File '{filepath}' not found."
            data = res.stdout
            if old_str not in data:
                return f"Error: old_str not found in {filepath}."
            data = data.replace(old_str, new_str)
            write_res = _docker_exec(
                ["tee", str(target_path)], input_text=data
            )
            if write_res.returncode != 0:
                return f"Error writing file '{filepath}': {write_res.stderr}"
            return "FILE EDITED"
        except subprocess.TimeoutExpired:
            return f"Error: Editing file '{filepath}' timed out."
        except Exception as e:
            return f"Error writing file '{filepath}': {e}"

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
    """List files in a directory matching a glob pattern.

    Parameters:
      - directory: Directory to inspect (defaults to repository root '.').
      - pattern: Glob pattern to filter files (e.g. '*.py', '*merge*').
    """
    if not pattern:
        pattern = "*"

    if CONTAINER_ID:
        py_script = """
import sys, pathlib
target_dir = sys.argv[1]
pattern = sys.argv[2]
testbed = pathlib.Path('/testbed').resolve()
root = pathlib.Path(target_dir)
if not root.is_absolute():
    root = testbed / root
if not root.exists() or not root.is_dir():
    print(f"Error: '{target_dir}' does not exist or is not a directory.")
    sys.exit(0)
matched = []
for p in root.rglob(pattern):
    if not p.is_file() or '.git' in p.parts:
        continue
    try:
        matched.append(str(p.resolve().relative_to(testbed)))
    except ValueError:
        matched.append(str(p.resolve()))
if not matched:
    print(f"No files matching pattern '{pattern}' found in '{target_dir}'.")
else:
    print("\\n".join(sorted(matched)))
"""
        try:
            res = _docker_exec(
                ["python3", "-c", py_script, directory, pattern],
                workdir="/testbed",
            )
            return res.stdout.strip()
        except Exception as e:
            return f"Error listing files: {e}"

    path = Path(directory)
    if not path.is_absolute():
        path = Path(TESTBED_PATH) / path
    if not path.exists() or not path.is_dir():
        return f"Error: '{directory}' does not exist or is not a directory."

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
    """Search for a regex pattern across files in the codebase.

    Parameters:
      - pattern: Regular expression pattern to search for.
      - file_pattern: Glob filter for filenames (e.g. '*.py'). Defaults to '*'.
    """
    if not file_pattern:
        file_pattern = "*"

    if CONTAINER_ID:
        py_script = """
import sys, re, pathlib
pattern = sys.argv[1]
file_pattern = sys.argv[2]
root = pathlib.Path('/testbed').resolve()
if not root.exists():
    print(f"Error: Root directory '{root}' does not exist.")
    sys.exit(0)
try:
    compiled = re.compile(pattern)
except re.error as e:
    print(f"Error: Invalid regular expression pattern '{pattern}': {e}")
    sys.exit(0)
results = []
for p in root.rglob(file_pattern):
    if not p.is_file() or '.git' in p.parts:
        continue
    try:
        with open(p, 'r', encoding='utf-8', errors='replace') as f:
            for l_nb, line in enumerate(f, start=1):
                if compiled.search(line):
                    results.append(f"{p.resolve()}:{l_nb} {line.rstrip()}")
    except (PermissionError, OSError):
        continue
if not results:
    print("No matches found.")
else:
    print("\\n".join(results))
"""
        try:
            res = _docker_exec(
                ["python3", "-c", py_script, pattern, file_pattern],
                workdir="/testbed",
            )
            return res.stdout.strip()
        except Exception as e:
            return f"Error searching code: {e}"

    root_path = Path(TESTBED_PATH).resolve()
    if not root_path.exists():
        return f"Error: Root directory '{root_path}' does not exist."

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
    """Find the definition of a function or class across the codebase.

    Parameters:
      - name: Exact function or class name to locate.
    """
    pattern = rf"^\s*(?:async\s+def|def|class)\s+{re.escape(name)}\b"
    return search_code(pattern=pattern, file_pattern="*.py")


@mcp.tool()
def find_references(name: str, filepath: str, line: int) -> str:
    """Find all usages and references of a symbol across Python files.

    Parameters:
      - name: Symbol name (function, class, variable).
      - filepath: Path of the file where the symbol is defined.
      - line: Line number of the definition.
    """
    pattern = rf"\b{re.escape(name)}\b"

    if CONTAINER_ID:
        py_script = """
import sys, re, pathlib
name = sys.argv[1]
filepath = sys.argv[2]
target_line = int(sys.argv[3]) if sys.argv[3].isdigit() else -1
root = pathlib.Path('/testbed').resolve()
pattern = rf"\\b{re.escape(name)}\\b"
try:
    compiled = re.compile(pattern)
except re.error as e:
    print(f"Error: Invalid pattern for name '{name}': {e}")
    sys.exit(0)
def_path = None
try:
    p = pathlib.Path(filepath)
    def_path = (p if p.is_absolute() else (root / p)).resolve()
except Exception:
    pass
results = []
for p in root.rglob("*.py"):
    if not p.is_file() or '.git' in p.parts:
        continue
    res_p = p.resolve()
    try:
        with open(res_p, 'r', encoding='utf-8', errors='replace') as f:
            for l_nb, line_content in enumerate(f, start=1):
                if def_path and res_p == def_path and l_nb == target_line:
                    continue
                if compiled.search(line_content):
                    results.append(f"{res_p}:{l_nb} {line_content.rstrip()}")
    except (PermissionError, OSError):
        continue
if not results:
    print("No matches found.")
else:
    print("\\n".join(results))
"""
        try:
            res = _docker_exec(
                ["python3", "-c", py_script, name, filepath, str(line)],
                workdir="/testbed",
            )
            return res.stdout.strip()
        except Exception as e:
            return f"Error finding references: {e}"

    root_path = Path(TESTBED_PATH).resolve()
    if not root_path.exists():
        return f"Error: Root directory '{root_path}' does not exist."

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
                            f"{resolved_file}:{line_nb} "
                            f"{line_content.rstrip()}"
                        )
        except (PermissionError, OSError):
            continue

    if not results:
        return "No matches found."

    return "\n".join(results)


# Execution Tools
@mcp.tool()
def run_tests() -> str:
    """Execute the repository test suite in the Docker testbed environment.

    Runs the official pytest evaluation. Returns test results, summary,
    and exit code (0 when all tests pass). Use this as the primary tool
    to verify bug fixes.
    """
    if CONTAINER_ID:
        try:
            res = _docker_exec(
                ["/bin/bash", "/eval.sh"], workdir="/testbed", timeout=300
            )
            return (
                f"Exit code: {res.returncode}\n"
                f"--- STDOUT ---\n{res.stdout}\n"
                f"--- STDERR ---\n{res.stderr}"
            )
        except subprocess.TimeoutExpired:
            return "Error: Test execution timed out (exceeded 300s)."
        except Exception as e:
            return f"Error executing tests in container: {e}"

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
    """Retrieve the unified git diff of all modifications made to the repo.

    Use this to inspect your changes before calling final_answer(get_patch()).
    """
    if CONTAINER_ID:
        try:
            res = _docker_exec(
                ["git", "-c", "core.fileMode=false", "diff"],
                workdir="/testbed",
                timeout=30,
            )
            if res.returncode != 0:
                return (
                    f"Error generating patch "
                    f"(exit code {res.returncode}): {res.stderr}"
                )
            return res.stdout
        except subprocess.TimeoutExpired:
            return "Error: git diff timed out (exceeded 30s)."
        except Exception as e:
            return f"Error executing git diff: {e}"

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
            return (
                f"Error generating patch "
                f"(exit code {res.returncode}): {res.stderr}"
            )
        return res.stdout
    except subprocess.TimeoutExpired:
        return "Error: git diff timed out (exceeded 30s)."
    except Exception as e:
        return f"Error executing git diff: {e}"


@mcp.tool()
def run_command(command: str, workdir: str = "") -> str:
    """Execute a shell command with the project's conda environment active.

    Parameters:
      - command: Shell command to execute. Do NOT use pip install.
      - workdir: Working directory (defaults to /testbed).
    Note: For testing the repository, prefer run_tests().
    Returns the command's stdout, stderr, and exit code.
    """
    # Guard against modifying environment packages via pip
    if "pip install" in command or "pip3 install" in command:
        return (
            "Error: Modifying the python environment with pip is forbidden. "
            "Use the pre-installed testbed environment and run_tests()."
        )

    if CONTAINER_ID:
        target_workdir = workdir if workdir else "/testbed"
        if not target_workdir.startswith("/"):
            target_workdir = f"/testbed/{target_workdir}"
        try:
            # Activate conda testbed environment before executing command
            cmd_with_env = (
                "source /opt/miniconda3/bin/activate testbed 2>/dev/null; "
                f"{command}"
            )
            res = _docker_exec(
                ["/bin/bash", "-c", cmd_with_env],
                workdir=target_workdir,
                timeout=120,
            )
            return (
                f"Exit code: {res.returncode}\n"
                f"--- STDOUT ---\n{res.stdout}\n"
                f"--- STDERR ---\n{res.stderr}"
            )
        except subprocess.TimeoutExpired:
            return f"Error: Command '{command}' timed out (exceeded 120s)."
        except Exception as e:
            return f"Error running command in container: {e}"

    if not workdir:
        cwd = Path(TESTBED_PATH)
    else:
        cwd = Path(workdir)
        if not cwd.is_absolute():
            cwd = Path(TESTBED_PATH) / cwd

    if not cwd.exists() or not cwd.is_dir():
        return (
            f"Error: Working directory '{cwd}' "
            f"does not exist or is not a directory."
        )

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
        "--container-id",
        type=str,
        default="",
        help="Docker container ID (overrides SWE_CONTAINER_ID)",
    )
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

    if args.container_id:
        CONTAINER_ID = args.container_id

    if args.transport in ("sse", "streamable-http"):
        mcp.run(transport=args.transport, port=args.port)
    else:
        mcp.run(transport="stdio")
