GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RESET  := $(shell tput -Txterm sgr0)

install:
	@echo "🔧 $(YELLOW)Installation...$(RESET)"
	@uv sync
	@echo "✅ $(GREEN)Environment ready !$(RESET)"



run:
	@echo "🚀 $(YELLOW)Project launch..$(RESET)"
	@uv run python3 -m src

debug:
	@echo "🐞 $(YELLOW)Debug mode enabled...$(RESET)"
	@uv run python3 -m pdb -m src

clean:
	@echo "🧹 $(YELLOW)Cleaning cache in progress...$(RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d \( -name ".mypy_cache" -o -name ".pytest_cache" \) -exec rm -rf {} +
	@rm -rf data/output
	@echo "✨ $(GREEN)Everything is clean !$(RESET)"

fclean: clean
	@echo "🧹 $(YELLOW)Cleaning .venv in progress...$(RESET)"
	@rm -rf .venv
	@echo "✨ $(GREEN)Everything is clean !$(RESET)"


lint:
	@echo "🔍 $(YELLOW)analysis...$(RESET)"
	@uv run flake8 src
	@uv run mypy src --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
	@echo "✅ $(GREEN)The analysis is complete !$(RESET)"

lint-strict: ## Analyse statique en mode strict
	@echo "🔍🔍🔍  $(YELLOW)strict analysis...$(RESET)"
	@uv run flake8 src
	@uv run mypy --strict src
	@echo "✅ $(GREEN)The analysis is complete!$(RESET)"

.PHONY: install run debug clean fclean lint lint-strict evalcode evaldocs index search search_dataset eval semantic hybrid kill