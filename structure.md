agent_smith/
├── pyproject.toml               # Dependencies managed with uv (Pydantic, etc.)
├── README.md                    # Project specifications and guidelines (in English)
├── BENCHMARK_REPORT.md          # Comparative benchmark report of 5 models on SWE-bench
├── sandbox_template.json        # Example sandbox configuration file
│
├── mcp_tools_mbpp.py            # MCP tools for MBPP benchmark (at root)
├── mcp_tools_swebench.py        # MCP tools for SWE-bench benchmark (at root)
│
├── agent_mbpp/                  # Executable module via `python -m agent_mbpp`
│   ├── __init__.py
│   └── __main__.py              # CLI entry point for MBPP
│
├── agent_swebench/              # Executable module via `python -m agent_swebench`
│   ├── __init__.py
│   └── __main__.py              # CLI entry point for SWE-bench
│
└── src/                         # Core agentic framework
    ├── __init__.py
    ├── models.py                # Pydantic models (SandboxConfig, StepMetrics, etc.)
    │
    ├── sandbox/                 # Sandbox engine
    │   ├── __init__.py
    │   ├── cli.py               # REPL entry point for `uv run sandbox`
    │   ├── executor.py          # Supervisor process / timeout / signals
    │   ├── worker.py            # Isolated child process (RLIMIT, builtins, hooks)
    │   ├── guards.py            # Import filtering, open restrictions, network guard
    │   └── manual.py            # Dynamic tool manual generator for prompts
    │
    ├── mcp/                     # Model Context Protocol integration
    │   ├── __init__.py
    │   ├── client.py            # MCP client (stdio and HTTP transports)
    │   └── wrappers.py          # Wraps MCP tools into native Python callables
    │
    ├── llm/                     # LLM interaction layer
    │   ├── __init__.py
    │   ├── client.py            # Multi-provider abstract client (OpenRouter, Groq, etc.)
    │   └── token_manager.py     # API key rotation, quota and retry management
    │
    ├── agent/                   # Agent loop orchestrator
    │   ├── __init__.py
    │   ├── loop.py              # Thought -> Code -> Observation cycle
    │   ├── parser.py            # Markdown extraction and XML/JSON to Python conversion
    │   └── prompt.py            # System prompt construction with examples
    │
    └── docker/                  # Container management for SWE-bench
        ├── __init__.py
        └── manager.py           # Container lifecycle and guaranteed cleanup