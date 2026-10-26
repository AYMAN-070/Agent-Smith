SRC := src agent_mbpp agent_swebench

all: help

help:
	@echo "Available targets:"
	@echo "  install        Install dependencies with uv"
	@echo "  lint           Run flake8 and mypy in strict mode"
	@echo "  sandbox        Launch interactive sandbox REPL"
	@echo "  sandbox-mbpp   Launch sandbox REPL with MBPP MCP tools"
	@echo "  sandbox-swe    Launch sandbox REPL with SWE-bench MCP tools"
	@echo "  run-mbpp       Run MBPP agent (TASK_FILE=... OUTPUT_FILE=...)"
	@echo "  run-swe        Run SWE-bench agent (TASK_FILE=... OUTPUT_FILE=...)"
	@echo "  clean          Remove Python and linter caches"
	@echo "  fclean         Remove caches and virtual environment"
	@echo "  re             Clean and reinstall dependencies"

install:
	uv sync

lint:
	uv run flake8 $(SRC)
	uv run mypy --strict $(SRC)

sandbox:
	uv run sandbox

sandbox-mbpp:
	uv run sandbox --mcp-stdio "python3 mcp_tools_mbpp.py" sandbox_template.json

sandbox-swe:
	uv run sandbox --mcp-stdio "python3 mcp_tools_swebench.py" sandbox_template.json

run-mbpp:
	uv run python -m agent_mbpp --task-file $(or $(TASK_FILE),taskmbpp.json) --output $(or $(OUTPUT_FILE),solution.json)

run-swe:
	uv run python -m agent_swebench --task-file $(or $(TASK_FILE),task.json) --output $(or $(OUTPUT_FILE),solution.json)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d \( -name ".mypy_cache" -o -name ".pytest_cache" -o -name ".ruff_cache" \) -exec rm -rf {} + 2>/dev/null || true

fclean: clean
	rm -rf .venv

re: fclean install

.PHONY: all help install lint sandbox sandbox-mbpp sandbox-swe run-mbpp run-swe clean fclean re

.PHONY: all help install lint sandbox sandbox-mbpp sandbox-swe run-mbpp run-swe clean fclean re

