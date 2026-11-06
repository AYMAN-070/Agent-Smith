*This project has been created as part of the 42 curriculum by gchmilew, ayhammou.*

# Agent Smith

Agent Smith is an autonomous **Code Agent** engineered to solve complex programming tasks without human intervention. Instead of relying on static one-shot prompts, the agent implements a closed **Thought → Code → Observation** reasoning loop (ReAct pattern).

The agent solves two complementary tiers of software engineering challenges:
1. **MBPP (Mostly Basic Python Problems)**: Algorithmic Python challenges requiring function synthesis and assertion testing.
2. **SWE-bench**: Real-world GitHub issues resolved inside isolated production Docker containers, requiring repository inspection, surgical code edits, test execution, and unified git diff generation.

Engineered without high-level agent orchestration frameworks (such as LangChain, CrewAI, or AutoGen)—using Python 3.10, Pydantic, and `uv`—Agent Smith relies on three foundational pillars:
- **Model Context Protocol (MCP)**: Dynamic tool discovery and execution via JSON-RPC.
- **Secure Sandbox**: Linux process isolation, kernel `RLIMIT` enforcement, network blocking, and import allowlisting.
- **Multi-Provider LLM Cascade**: Automatic fallback across API providers with intelligent rate-limit (HTTP 429) recovery.

---

# Description

Traditional LLMs often hallucinate or fail when attempting to write software in a single pass. Agent Smith bridges the gap between language generation and real-world execution by giving the LLM an interactive environment.

The agent operates through an iterative control loop:
1. **Analyze**: The agent examines the issue description and plans its next action (**Thought**).
2. **Act**: The agent writes a self-contained Python script utilizing available tools (**Code**).
3. **Observe**: The script executes in a secure sandbox, returning stdout, stderr, or test failures (**Observation**).
4. **Refine**: The agent evaluates feedback, corrects mistakes, and iterates until all verification tests pass, submitting its solution via `final_answer()`.

---

# Instructions

### Prerequisites
- **Linux** (x86_64 recommended).
- **Python 3.10+** and **uv** package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **Docker** daemon installed and running (required for SWE-bench execution).

### Installation
Clone the repository and install dependencies using `uv`:
```bash
git clone <repository_url> Agent-Smith
cd Agent-Smith
make install
```

### Environment Configuration
Create a `.env` file at the root of the repository with your API keys:
```env
# Primary Providers
NVIDIA_API_KEY=nvapi-...
OPENROUTER_API_KEY=sk-or-v1-...
GEMINI_API_KEY=AIzaSy...

# Optional Direct Providers
OPENAI_API_KEY=sk-proj-...
GROQ_API_KEY=gsk_...
```

### Command-Line Usage

#### 1. Code Quality & Linting
Validate strict typing and styling across all files (zero warnings allowed):
```bash
make lint-strict
```

#### 2. Running MBPP Agent
Execute the agent on algorithmic challenges:
```bash
make run-mbpp TASK_FILE=taskmbpp.json OUTPUT_FILE=solution.json
```

#### 3. Running SWE-bench Agent
Resolve real-world GitHub issues in Docker:
```bash
make run-swe TASK_FILE=task.json OUTPUT_FILE=solution.json
```

#### 4. Interactive Sandbox REPL
Test the execution sandbox manually with connected MCP tools:
```bash
# Standalone sandbox
make sandbox

# Sandbox connected to MBPP tools
make sandbox-mbpp

# Sandbox connected to SWE-bench tools
make sandbox-swe
```

---

# System Architecture

The project is structured into clean, decoupled layers separating orchestration, network communication, isolated execution, and tool protocols:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             AGENT ORCHESTRATOR                              │
│         (CLI Entry, Task Loading, Prompt Generation, Metrics & Provenance)  │
└───────────────────▲───────────────────────────────────────▲─────────────────┘
                    │                                       │
     Payload / Text │ Structured Response      Raw Code /   │ Captured
        (Tokens,    │                             Tests     │ Observation /
         Latency)   ▼                                       ▼ Traceback
┌──────────────────────────────────────┐  ┌───────────────────────────────────┐
│          LLM PROVIDER LAYER          │  │          SANDBOX BOUNDARY         │
│  - Multi-Key & Provider Fallback     │  │  - Child Process Isolation        │
│  - Quota (429) & Error Auto-Switch   │  │  - Kernel RLIMIT & Network Block  │
│  - Standardized OpenAI Schema        │  │  - Import Allowlist & final_answer│
└──────────────────────────────────────┘  └─────────────────▲─────────────────┘
                                                            │ stdio / HTTP
                                                            │ (JSON-RPC 2.0)
                                          ┌─────────────────▼─────────────────┐
                                          │            MCP SERVERS            │
                                          │  - mcp_tools_mbpp (test runner)   │
                                          │  - mcp_tools_swebench (fs, git,   │
                                          │    search, pytest in container)   │
                                          └───────────────────────────────────┘
```


### Directory Structure
```
Agent-Smith/
├── agent_mbpp/              # CLI entry point for MBPP agent
├── agent_swebench/          # CLI entry point for SWE-bench agent
├── benchmarks/              # Benchmark suite, tasks, and run traces
│   ├── assets/              # Performance, Pareto, and token accumulation SVG charts
│   ├── runs/                # 40 backing JSON solution traces (model x task)
│   └── tasks/               # Standardized SWE-bench tasks (xarray, django, sympy, etc.)
├── src/
│   ├── agent/               # Agent control loop, prompt builders, output sanitizers
│   │   ├── base_loop.py     # Base agent loop with metrics and limit enforcement
│   │   ├── loop.py          # Iterative Thought-Code-Observation loop (MBPP & SWE)
│   │   ├── prompt.py        # System prompt builder with step budgets & Two-Phase rules
│   │   └── sandbox_output_handler.py # Conda noise cleaner & observation truncator
│   ├── docker_handler.py    # Docker container lifecycle manager
│   ├── llm/                 # LLM API communication and response parsing
│   │   ├── llm.py           # Request handler & token telemetry extraction
│   │   ├── parser.py        # Multi-format parser (Hermes, XML, ReAct, Markdown)
│   │   └── provider.py      # Multi-provider cascade (NVIDIA, Gemini, OpenRouter)
│   ├── mcp/                 # MCP client (stdio & Streamable HTTP transport)
│   │   ├── client.py        # Dynamic tool discovery, resources, and prompts
│   │   └── wrappers.py      # Dynamic tool wrapper generators
│   ├── models.py            # Pydantic schemas (SolutionOutput, StepMetrics, etc.)
│   ├── rules.py             # Resource limits and budget definitions
│   └── sandbox/             # Security boundary & code executor
│       ├── cli.py           # Interactive REPL interface
│       ├── executor.py      # Child process runner, RLIMIT, network blocker
│       └── manual.py        # Auto-generated tools documentation for system prompt
├── mcp_tools_mbpp.py        # Standalone stdio JSON-RPC MCP server for MBPP
├── mcp_tools_swebench.py    # Standalone FastMCP server for SWE-bench
├── sandbox_template.json    # JSON template for sandbox security limits and paths
├── execution_flow.png       # Comprehensive decision graph and execution flow
├── BENCHMARK_REPORT.md      # Multi-model evaluation report
├── Makefile                 # Build, lint-strict, sandbox, and agent execution targets
├── pyproject.toml           # Project dependencies and tool settings
└── uv.lock                  # Pinned dependency lockfile
```

---

# Agent Loop Explanation

The core intelligence of Agent Smith resides in `src/agent/loop.py`. It operates as a state machine:

```
    ┌────────────────┐
    │  Task Input    │
    │  (JSON / Spec) │
    └───────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ Prompt Builder  │ ◄──────────────────────────────────────────────┐
   │ (System + Tools)│                                                │
   └────────┬────────┘                                                │
            │                                                         │
            ▼                                                         │
   ┌─────────────────┐                                                │
   │  LLM Provider   │                                                │
   │  (Thought+Code) │                                                │
   └────────┬────────┘                                                │
            │                                                         │
            ▼                                                         │
   ┌─────────────────┐                                                │
   │  Code Parser    │                                                │
   │ (Extract Block) │                                                │
   └────────┬────────┘                                                │
            │                                                         │
            ▼                                                         │
   ┌─────────────────┐                                                │
   │ Secure Sandbox  │                                                │
   │ (Execute Code)  │                                                │
   └────────┬────────┘                                                │
            │                                                         │
            ▼                                                         │
   ┌─────────────────┐       No (Tests fail / need more info)         │
   │  Observation &  │ ───────────────────────────────────────────────┘
   │ Output Handler  │
   └────────┬────────┘
            │ Yes (Verification passed)
            ▼
   ┌─────────────────┐
   │ `final_answer`  │ ──► Produces solution.json
   └─────────────────┘
```
> **Note**: The diagram above is a simplified high-level representation of the agent's runtime architecture. For an exhaustive graph illustrating every decision branch, refer to the full diagram: [Detailed Execution Flow Diagram](execution_flow.png).

### Execution Steps
1. **Context Initialization**: The prompt builder constructs the system prompt containing the dynamically generated tools manual, operational rules, and problem statement.
2. **Generation & Telemetry**: The LLM generates Python code. The provider records wall-clock latency, input tokens, output tokens, and retry counts.
3. **Extraction & Execution**: Executable Python code is parsed from markdown blocks and dispatched to the isolated sandbox.
4. **Observation Sanitization**: Output is sanitized via `SandboxOutputHandler`:
   - Strips noisy bash debug traces (`+ conda activate...`).
   - Truncates oversized outputs beyond 4,000 characters to prevent quadratic token expansion.
   - Detects when tests pass to inject immediate submission reminders.
5. **Termination Conditions**:
   - **Success**: The LLM calls `final_answer(answer)` with the function string (MBPP) or git diff (SWE-bench).
   - **Budget Limit**: The loop terminates gracefully if `max_iterations` (30) or token limits are exceeded.

---

# Sandbox Design

The sandbox (`src/sandbox/executor.py`) acts as a strict security barrier executing untrusted LLM code without compromising host integrity. It incorporates five complementary defensive mechanisms:

1. **Process Isolation (`multiprocessing.Process`)**:
   - Untrusted code runs in a separated fork. Uncaught exceptions, memory errors, or `sys.exit()` cannot crash the orchestrator.
   - Execution is bounded by a strict wall-clock timeout (`max_execution_time_seconds`). Runaway processes are killed via `process.kill()`.

2. **Kernel Resource Limits (`resource.setrlimit`) & Process Timeout**:
   - Caps maximum address space (`RLIMIT_AS`) to 512 MB, mitigating memory-exhaustion denial-of-service.
   - Strict wall-clock timeouts (`max_execution_time_seconds`) are enforced at the process boundary to terminate infinite loops and runaway executions.

3. **Network Isolation (`GuardedSocket`)**:
   - External network access is strictly blocked inside the sandbox.
   - `socket.socket` is replaced by `GuardedSocket`, restricting connections exclusively to local loopback (`127.0.0.1`, `localhost`) required for local MCP server communication. Any outbound external connection immediately raises `PermissionError`. Low-level resolution functions (`gethostbyname`, `socketpair`, etc.) are neutralized.

4. **Namespace Sanitization & Restricted Built-ins**:
   - Standard `__builtins__` is replaced with an allowlist of safe functions (`print`, `len`, `range`, `dict`, `int`, etc.).
   - Hazardous primitives capable of arbitrary code execution or shell escapes (`eval`, `exec`, `breakpoint`, `compile`) are removed.
   - Filesystem access is strictly mediated: `open` is replaced by `create_safe_open`, permitting access only within explicitly authorized directories (`/testbed`, `/tmp/agent`).

5. **Import Allowlisting**:
   - Python's `__import__` is replaced by an import guard (`create_safe_import`). Only modules specified in `authorized_imports` (e.g. `math`, `json`, `re`, `collections`) can be imported. Unauthorized imports raise `ImportError`.

---

# Tool Implementation Details

Tools are exposed via the **Model Context Protocol (MCP)** and dynamically injected into the sandbox environment as global Python functions.

### SWE-bench Tool Suite (`mcp_tools_swebench.py`)
All tools execute directly against the testbed repository inside the Docker container:
- `read_file(filepath: str, start_line: int, end_line: int)`: Reads lines with line numbers formatted identically to `cat -n`.
- `edit_file(filepath: str, old_str: str, new_str: str)`: Applies exact, surgical text replacements.
- `list_files(directory: str, pattern: str)`: Discovers files matching glob patterns.
- `search_code(pattern: str, file_pattern: str)`: Fast regex/grep code search across the project.
- `search_function_or_class_definition_in_code(name: str)`: Locates AST symbol declarations.
- `find_references(name: str, filepath: str, line: int)`: Finds all symbol usages across the codebase.
- `run_tests()`: Executes the repository's evaluation script (e.g., `pytest`) and returns stdout, stderr, and exit codes.
- `get_patch()`: Generates the unified git diff of all modifications made to the repository.
- `run_command(command: str, workdir: str)`: Executes arbitrary shell commands within the isolated container.

### MBPP Tool Suite (`mcp_tools_mbpp.py`)
- `run_tests(candidate_code: str, test_assertions: list[str])`: Evaluates candidate functions against public unit test assertions in an isolated sub-sandbox.

### MCP Resources & Prompts
- **Resources**: Exposes static documentation via URIs (e.g., `mbpp://guidelines`, `swebench://guidelines`).
- **Prompts**: Exposes reusable prompt templates (e.g., `solve_mbpp_task`, `debug_swebench_issue`) accessible through the MCP protocol.

---

# Benchmark Results and Analysis

In compliance with **Section V.7 (Model Benchmark Report)** of the 42 curriculum, we evaluated **8 language models** across **3 providers** on **5 official SWE-bench tasks**:

### Tested Models & Providers
1. **NVIDIA NIM**: `nvidia/nemotron-3-ultra-550b-a55b`
2. **Gemini**: `gemini-3.5-flash-lite`
3. **Gemini**: `gemini-3.1-flash-lite`
4. **OpenRouter**: `openai/gpt-4o`
5. **OpenRouter**: `openai/gpt-4o-mini`
6. **OpenRouter**: `meta-llama/llama-3.3-70b-instruct`
7. **OpenRouter**: `qwen/qwen-2.5-coder-32b-instruct`
8. **OpenRouter**: `mistralai/mistral-small-24b-instruct-2501`

### Evaluated SWE-bench Tasks
- `pydata__xarray-4629` (`pydata/xarray`): Attribute copying bug during dataset merge.
- `django__django-11066` (`django/django`): ContentTypes migration rename handling.
- `sympy__sympy-13480` (`sympy/sympy`): NameError typo in symbolic hyperbolic substitution.
- `scikit-learn__scikit-learn-13439` (`scikit-learn/scikit-learn`): Pipeline slicing special method protocol (`__len__`).
- `sympy__sympy-18189` (`sympy/sympy`): Diophantine equation solver permutation symmetry.

### Executive Summary
| Metric | Leader | Key Takeaway |
| :--- | :--- | :--- |
| **Success Rate** | `gpt-4o-mini` & `nemotron-3-ultra` | Successfully located root-cause files in $\le 2$ steps and passed regression tests. |
| **Token Economy** | `gpt-4o-mini` | Consumed under 130k tokens per task—well within the 300k limit. |
| **Latency** | `gpt-4o-mini` | Average response latency of 1.4s vs 8.1s for high-parameter MoE models. |
| **Discipline** | `qwen-2.5-coder-32b` | Zero steps elapsed between first test pass and `final_answer` submission. |

> Complete results, provider reliability metrics, intermediary metrics, and ablation studies are documented in detail in [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md).

---

# Resources

### References
- [FastMCP](https://github.com/jlowin/fastmcp)
- [SWE-bench](https://www.swebench.com)
- [Python Sandbox](https://docs.python.org/3/library/resource.html)

### AI Usage & Collaboration

In accordance with 42 curriculum standards and the 42 AI Charter, Artificial Intelligence (primarily **Google Gemini**) was utilized throughout the conception, development, and debugging of Agent Smith as an interactive pair-programming partner and technical sounding board:

- **Ecosystem & Protocol Exploration**: Accelerating comprehension of the Model Context Protocol (MCP) JSON-RPC 2.0 specifications (stdio transport, lifecycle handshakes, tool schemas) and dissecting SWE-bench Docker container execution harness requirements.
- **Architectural Brainstorming**: Investigating implementation strategies for strict sandbox security (process isolation, `RLIMIT_AS`, socket monkeypatching, and path scoping) using standard Python tools without relying on black-box agent frameworks.
- **AST Manipulation & REPL Dynamics**: Exploring Python's `ast` module to implement automatic expression wrapping (`transform_to_interactive_code`), ensuring unassigned tool outputs are visibly captured by stdout without explicit `print()` calls.
- **Telemetry & Output Heuristics**: Diagnosing quadratic token explosion during lengthy pytest runs, leading to our dual-ended observation windowing heuristic (retaining head and tail lines of verbose tracebacks).
- **Container Cleanup & Signals**: Refining Docker process lifecycle management and signal trapping (`SIGINT`, `SIGTERM`, `SIGHUP`) to guarantee zero orphaned containers.

All code, architectural choices, and prompts were iteratively tested, integrated, and fully mastered by the authors, ensuring complete intellectual ownership and live defense readiness.
