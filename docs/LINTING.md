# Linting and Code Quality Standards

This document outlines the linting and code quality standards for the DocsCopilot project.

## Overview

DocsCopilot uses a combination of tools to ensure code quality and consistency:

- **Black**: Code formatting
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking
- **Pre-commit**: Git hooks for automated checks

## Tools Configuration

### Black

Black is configured in `pyproject.toml` with the following settings:

- **Line length**: 88 characters
- **Target Python version**: 3.11+

Black automatically formats Python code according to PEP 8 style guidelines with some opinionated choices.

**Usage:**
```bash
# Check formatting
make lint

# Auto-format code
make format
# or
black .
```

### Ruff

Ruff is configured in `pyproject.toml` and combines multiple linting tools:

- **pycodestyle** (E, W): PEP 8 style guide enforcement
- **pyflakes** (F): Logical errors and unused imports
- **isort** (I): Import sorting
- **flake8-bugbear** (B): Common bugs and design problems
- **flake8-comprehensions** (C4): Better comprehensions
- **pyupgrade** (UP): Modernize Python syntax

**Configuration:**
- Line length: 88 characters (handled by Black)
- Target Python version: 3.11+
- E501 (line too long) is ignored as Black handles formatting

**Usage:**
```bash
# Run linting (included in make lint)
ruff check .

# Auto-fix issues
ruff check --fix .
```

### MyPy

MyPy performs static type checking with strict settings:

- **Strict type checking**: Untyped definitions are disallowed
- **Namespace packages**: Enabled for proper package detection
- **Explicit package bases**: Required for proper module resolution

**Configuration highlights:**
- `disallow_untyped_defs`: All function definitions must have type hints
- `disallow_incomplete_defs`: Function signatures must be complete
- `check_untyped_defs`: Check untyped function definitions
- `strict_optional`: Treat Optional types strictly

**Usage:**
```bash
# Run type checking (included in make lint)
make type-check
# or
mypy src/ --namespace-packages --explicit-package-bases
```

## Pre-commit Hooks

Pre-commit hooks automatically run linting checks before commits. This ensures code quality before it enters the repository.

**Setup:**
```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files
```

**Hooks configured:**
- Trailing whitespace removal
- End of file fixer
- YAML/JSON/TOML validation
- Large file detection
- Merge conflict detection
- Black formatting
- Ruff linting
- MyPy type checking

## Makefile Targets

The project provides several Makefile targets for linting:

- `make lint`: Run all linters (black, ruff, mypy) and check formatting
- `make format`: Auto-format code with black
- `make type-check`: Run mypy type checking only

## Code Quality Standards

### Type Hints

All function definitions must include type hints:

```python
def process_data(data: dict[str, Any]) -> list[str]:
    """Process data and return results."""
    ...
```

### Import Organization

Imports are automatically sorted by isort (via Ruff) with the following order:
1. Standard library imports
2. Third-party imports
3. Local application imports

### Line Length

Maximum line length is 88 characters. Black will automatically wrap lines when formatting.

### Code Style

Follow PEP 8 guidelines. Black handles most formatting automatically, but ensure:
- Use meaningful variable names
- Write docstrings for all public functions and classes
- Keep functions focused and small
- Use type hints consistently

## Continuous Integration

All pull requests should pass linting checks. The CI pipeline runs:
- `make lint` to verify code quality
- `make test` to ensure tests pass

## Troubleshooting

### MyPy Errors

If MyPy reports errors about missing types:
1. Add type hints to function signatures
2. Use `typing.Any` for complex types if needed
3. Use `# type: ignore` comments sparingly and with justification

### Ruff Errors

Most Ruff errors can be auto-fixed:
```bash
ruff check --fix .
```

### Black Formatting

If Black wants to reformat code:
```bash
make format
```

This will automatically format all Python files according to Black's rules.

## Additional Resources

- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)
