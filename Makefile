.PHONY: help install install-dev test test-unit test-integration lint format type-check clean build run

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := pip3
PYTEST := pytest
BLACK := black
RUFF := ruff
MYPY := mypy
PODMAN_COMPOSE := podman-compose

# Colors for help output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Display available targets
	@echo "$(BLUE)Available targets:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Note:$(NC) For container operations like 'stop' and 'logs', use 'podman-compose stop' and 'podman-compose logs' directly."
	@echo "$(YELLOW)Note:$(NC) For formatting, run 'black .' directly or it's included in 'make lint'."

install: ## Install project and development dependencies
	$(PIP) install -e .
	$(PIP) install -r requirements-dev.txt

install-dev: install ## Alias for install (installs dev dependencies by default)

test: ## Run all tests
	$(PYTEST) tests/

test-unit: ## Run unit tests only
	$(PYTEST) -m unit tests/

test-integration: ## Run integration tests only
	$(PYTEST) -m integration tests/

lint: ## Run all linters (black, ruff, mypy) and check formatting
	@echo "$(BLUE)Running black (format check)...$(NC)"
	$(BLACK) --check --diff .
	@echo "$(BLUE)Running ruff...$(NC)"
	$(RUFF) check .
	@echo "$(BLUE)Running mypy...$(NC)"
	$(MYPY) src/
	@echo "$(GREEN)All linting checks passed!$(NC)"

format: ## Auto-format code with black
	$(BLACK) .

type-check: ## Run mypy type checking only
	$(MYPY) src/

build: ## Build Podman containers
	$(PODMAN_COMPOSE) build

run: ## Run containers locally via podman-compose
	$(PODMAN_COMPOSE) up -d

clean: ## Remove build artifacts, cache files, and Python bytecode
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	rm -rf build/ dist/ .eggs/ 2>/dev/null || true
	@echo "$(GREEN)Clean complete!$(NC)"

