# DocsCopilot Implementation Plan

This document outlines the implementation plan for DocsCopilot, organized as issues/tasks. Each issue represents a discrete unit of work that can be implemented and tested independently.

## Project Overview

DocsCopilot is an AI-driven documentation automation system built using MCP (Model Context Protocol) servers. The system consists of:
- 3 MCP Servers (Code Context, Templates+Style, Docs Repo)
- Containerized deployment
- Python-based implementation
- Makefile-based build, test, and lint workflows

---

## Issue 1: Project Structure and Base Setup

**Priority:** High  
**Estimated Effort:** 2-3 hours

### Description
Set up the basic project structure, Python package configuration, and development environment.

### Tasks
- [ ] Create Python package structure:
  ```
  docscopilot/
  ├── src/
  │   ├── code_context_server/
  │   ├── templates_style_server/
  │   └── docs_repo_server/
  ├── tests/
  │   ├── unit/
  │   └── integration/
  ├── config/
  ├── scripts/
  └── container/
  ```
- [ ] Create `pyproject.toml` with:
  - Project metadata
  - Dependencies (mcp, fastapi, pydantic, etc.)
  - Build configuration
  - Development dependencies (pytest, black, ruff, mypy, etc.)
- [ ] Create `requirements.txt` and `requirements-dev.txt`
- [ ] Create `.gitignore` for Python projects
- [ ] Create `.python-version` or `pyproject.toml` with Python version specification (3.11+)
- [ ] Create `README.md` with setup instructions

### Acceptance Criteria
- Project structure follows Python best practices
- Dependencies are properly specified
- Project can be installed in development mode (`pip install -e .`)

---

## Issue 2: Makefile for Build, Test, and Lint

**Priority:** High  
**Estimated Effort:** 2-3 hours

### Description
Create comprehensive Makefile with targets for building, testing, linting, and container operations.

### Tasks
- [ ] Create `Makefile` with the following essential targets:
  - `make install` - Install project and development dependencies
  - `make test` - Run all tests (use pytest markers for unit/integration: `pytest -m unit` or `pytest -m integration`)
  - `make lint` - Run all linters (black, ruff, mypy) and check formatting
  - `make build` - Build Podman containers
  - `make run` - Run containers locally via podman-compose
  - `make clean` - Remove build artifacts, cache files, and Python bytecode
  - `make help` - Display available targets

**Note:** For container operations like `stop` and `logs`, use `podman-compose stop` and `podman-compose logs` directly. For formatting, run `black .` directly or it's included in `make lint`.

### Acceptance Criteria
- All Makefile targets work correctly
- Linting catches common Python issues
- Tests can be run via Makefile
- Podman operations work via Makefile

---

## Issue 3: Podman Containerization Setup

**Priority:** High  
**Estimated Effort:** 3-4 hours

### Description
Set up Podman configuration for running MCP servers as containers.

### Tasks
- [ ] Create `Containerfile` (or `Dockerfile` for compatibility) for MCP server container:
  - Base Python image (Python 3.11+)
  - Install dependencies
  - Copy source code
  - Set up entrypoint
  - Expose appropriate ports
- [ ] Create `podman-compose.yml` (or `docker-compose.yml` for compatibility):
  - Define services for each MCP server
  - Configure networking between services
  - Set up volumes for development
  - Configure environment variables
- [ ] Create `.containerignore` (or `.dockerignore` for compatibility) file
- [ ] Create `container/` directory with:
  - Entrypoint scripts
  - Health check scripts
  - Configuration templates
- [ ] Document container configuration and environment variables
- [ ] Ensure Podman compatibility (rootless mode support)

### Acceptance Criteria
- All MCP servers can be built as Podman containers
- Containers can be run via podman-compose
- Containers are properly networked
- Health checks work correctly
- Rootless Podman mode is supported

---

## Issue 4: Code Context MCP Server

**Priority:** High  
**Estimated Effort:** 8-10 hours

### Description
Implement the Code Context MCP Server that provides feature metadata, code examples, and change diff context. The server works with repositories already present in the workspace - it does NOT clone repositories. Users are responsible for ensuring repositories are available in the workspace before using the server.

### Architecture
- **Filesystem access**: Direct file reads from workspace paths
- **Git commands**: Use `git` CLI on existing repositories in workspace (git diff, git log, git show, git grep)
- **No cloning**: Server assumes repos are already available in workspace
- **No external APIs**: Parse feature metadata from git commits, tags, branches, and commit messages

### Tasks
- [ ] Set up MCP server framework (using `mcp` Python SDK)
- [ ] Create git utilities module (`git_utils.py`):
  - Helper functions for git commands (log, diff, show, ls-files)
  - Execute git commands via subprocess
  - Parse git output into structured data
- [ ] Create code parser utilities (`code_parser.py`):
  - AST parsing for Python files
  - Extract function/class definitions
  - Parse docstrings and code blocks
- [ ] Implement `get_feature_metadata(feature_id)` function:
  - Search git repository in workspace for feature references:
    - Use `git log --grep="<feature_id>"` to find commits mentioning the feature
    - Use `git branch -a --contains <commit>` to find branches
    - Use `git tag --contains <commit>` to find tags
    - Parse commit messages for issue/PR references (e.g., "Fixes #123", "Closes FEAT-217")
  - Identify code paths:
    - Use `git diff <base>..<feature-branch>` to find changed files
    - Use `git log --oneline --name-only --grep="<feature_id>"` to get file paths
  - Find associated tests:
    - Search for test files matching changed code paths (e.g., `test_*.py`, `*_test.py`)
    - Use `git ls-files` with patterns to find test files
  - Extract metadata from commit messages:
    - Parse structured commit messages (conventional commits format)
    - Extract description, type, scope from commit messages
  - Return structured metadata (feature_id, commits, branches, tags, code_paths, test_paths, description, related_issues)
- [ ] Implement `get_code_examples(path)` function:
  - Read file directly from filesystem using `pathlib` or `open()`
  - Parse code using AST for Python files
  - Extract function definitions, class definitions, code blocks with comments, docstrings
  - Format examples for documentation:
    - Include relevant context (imports, surrounding code)
    - Preserve code formatting
    - Add language identifiers for markdown code blocks
  - Return structured examples (path, examples with type, name, code, docstring, line_numbers)
- [ ] Implement `get_changed_endpoints(diff)` function:
  - Parse git diff using `git diff` command or parse diff string
  - Identify API endpoint changes:
    - For Python/FastAPI: Look for `@app.route()`, `@router.get()`, `@router.post()` decorators
    - For REST APIs: Parse route definitions, HTTP methods, paths
    - Use AST parsing for Python files to extract function signatures
  - Extract API signatures:
    - Function name, parameters, return types
    - HTTP method and path
    - Request/response schemas (if available in code)
  - Detect new endpoints vs modified endpoints
  - Return structured endpoint information (endpoints with method, path, function, file, signature, status, line_numbers)
- [ ] Add configuration support:
  - `WORKSPACE_ROOT`: Root directory containing repositories (default: current directory)
  - `GIT_BINARY`: Path to git binary (default: "git")
  - `SUPPORTED_LANGUAGES`: Languages to parse (default: ["python"])
- [ ] Add error handling:
  - If repository not found in workspace: Return clear error message
  - If feature_id not found: Return empty result with warning
  - If file path doesn't exist: Return file not found error
  - If git command fails: Log error and return partial results if possible
- [ ] Write unit tests:
  - Mock filesystem and git commands
  - Test each function with various inputs
  - Test error handling scenarios
- [ ] Write integration tests:
  - Create temporary git repos with sample commits/branches
  - Test with real git repositories in workspace
  - Verify end-to-end functionality

### File Structure
```
src/code_context_server/
├── __init__.py
├── server.py                 # MCP server setup
├── feature_metadata.py      # get_feature_metadata implementation
├── code_examples.py          # get_code_examples implementation
├── changed_endpoints.py      # get_changed_endpoints implementation
├── git_utils.py              # Git command helpers
├── code_parser.py            # AST parsing utilities
└── models.py                 # Pydantic models for responses
```

### Dependencies
- `mcp` - MCP Python SDK
- `pydantic` - Data validation
- `GitPython` or subprocess for git commands
- `ast` - Python AST parsing (stdlib)
- `pathlib` - File path handling (stdlib)

### Acceptance Criteria
- Server responds to MCP protocol requests
- All three functions work correctly with existing workspace repositories
- No git clone operations are performed
- Error handling is robust (handles missing repos, files, git failures)
- Tests pass with >80% coverage
- Works with repositories already available in workspace

---

## Issue 5: Templates + Style MCP Server

**Priority:** High  
**Estimated Effort:** 6-8 hours

### Description
Implement the Templates + Style MCP Server that provides documentation templates, style guides, and glossary. The server uses a "Layered Lookup" approach to find resources:
1. **Configured Path**: Checks if an external path is configured (via environment variable).
2. **Workspace Overrides**: Checks for a `.docscopilot/` directory in the user's workspace.
3. **Built-in Defaults**: Falls back to default templates bundled with the package.

### Tasks
- [ ] Set up MCP server framework
- [ ] Create template storage system (Filesystem based):
  - Define template structure for each doc type (Concept, Task, API Reference, Release Notes, Feature Overview, Configuration Reference)
  - Implement Layered Lookup logic: Config -> Workspace (`.docscopilot/templates`) -> Defaults (`src/templates_style_server/defaults`)
- [ ] Create default templates:
  - Bundle standard Jinja2 templates for all doc types in `src/templates_style_server/defaults/templates/`
  - Create default style guide (YAML) in `src/templates_style_server/defaults/style_guides/`
  - Create default glossary (YAML) in `src/templates_style_server/defaults/glossaries/`
- [ ] Implement `get_template(doc_type)` function:
  - Validate doc_type
  - specific lookup for template file (e.g., `concept.md.j2`)
  - Return template content
- [ ] Implement `get_style_guide(product)` function:
  - Load style guide from configured layers
  - Return style rules (heading structure, tone, formatting)
- [ ] Implement `get_glossary()` function:
  - Load glossary entries from configured layers
  - Return terminology definitions
- [ ] Add configuration support:
  - `DOCSCOPILOT_TEMPLATES_PATH`: Optional path to external templates repo
- [ ] Add error handling and logging
- [ ] Write unit tests (test lookup priority)
- [ ] Write integration tests

### Acceptance Criteria
- Server responds to MCP protocol requests
- Layered lookup works: Workspace overrides take precedence over defaults
- Default templates are available without any user configuration
- Style guides and glossaries are loaded correctly
- Tests pass with >80% coverage

---

## Issue 6: Docs Repo MCP Server

**Priority:** High  
**Estimated Effort:** 10-12 hours

### Description
Implement the Docs Repo MCP Server that abstracts documentation repository operations (same-repo or external-repo).

### Tasks
- [ ] Set up MCP server framework
- [ ] Implement repository abstraction layer:
  - Support same-repo mode (docs in same repository)
  - Support external-repo mode (docs in separate repository)
  - Handle authentication for external repos
- [ ] Implement `suggest_doc_location(feature_id)` function:
  - Analyze feature metadata
  - Determine appropriate doc type
  - Suggest file path based on repo structure rules
  - Handle both same-repo and external-repo scenarios
- [ ] Implement `write_doc(path, content)` function:
  - Validate path
  - Create directory structure if needed
  - Write markdown file
  - Handle both same-repo and external-repo scenarios
- [ ] Implement `open_pr(branch, title, description)` function:
  - Create git branch
  - Commit changes
  - Push branch
  - Create pull request via API (GitHub/GitLab)
  - Handle authentication securely
- [ ] Add configuration for repo settings (same vs external, paths, etc.)
- [ ] Add error handling and logging
- [ ] Write unit tests
- [ ] Write integration tests

### Acceptance Criteria
- Server responds to MCP protocol requests
- All three functions work correctly
- Both same-repo and external-repo modes work
- PR creation works with proper authentication
- Tests pass with >80% coverage

---

## Issue 7: MCP Server Configuration Management

**Priority:** Medium  
**Estimated Effort:** 4-5 hours

### Description
Implement configuration management system for all MCP servers.

### Tasks
- [ ] Create configuration schema using Pydantic:
  - Server settings (host, port, logging)
  - Repository settings (same-repo vs external-repo, paths)
  - **Resource paths:** `DOCSCOPILOT_TEMPLATES_PATH`
  - Authentication credentials (secure storage)
- [ ] Support configuration via:
  - Environment variables
  - Configuration files (YAML/TOML)
  - Default values
- [ ] Create configuration validation
- [ ] Document configuration options
- [ ] Add example configuration files

### Acceptance Criteria
- Configuration is validated on startup
- Environment variables override file config
- Resource paths are correctly parsed and validated
- Sensitive data is handled securely
- Configuration is well-documented

---

## Issue 8: Logging and Monitoring

**Priority:** Medium  
**Estimated Effort:** 3-4 hours

### Description
Implement comprehensive logging and basic monitoring for all MCP servers.

### Tasks
- [ ] Set up structured logging (using `structlog` or `logging`):
  - Request/response logging
  - Error logging with stack traces
  - Performance metrics
- [ ] Configure log levels and output formats
- [ ] Add request ID tracking
- [ ] Create log rotation configuration
- [ ] Add basic health check endpoints
- [ ] Document logging configuration

### Acceptance Criteria
- All servers log requests and responses
- Errors are logged with sufficient context
- Logs are structured and parseable
- Health checks work correctly

---

## Issue 9: Unit Test Suite

**Priority:** High  
**Estimated Effort:** 8-10 hours

### Description
Create comprehensive unit test suite for all MCP servers.

### Tasks
- [ ] Set up pytest configuration (`pytest.ini` or `pyproject.toml`)
- [ ] Create test fixtures:
  - Mock repositories
  - Mock file systems
  - Mock API responses
- [ ] Write unit tests for Code Context Server:
  - Test `get_feature_metadata`
  - Test `get_code_examples`
  - Test `get_changed_endpoints`
- [ ] Write unit tests for Templates + Style Server:
  - Test `get_template`
  - Test `get_style_guide`
  - Test `get_glossary`
- [ ] Write unit tests for Docs Repo Server:
  - Test `suggest_doc_location`
  - Test `write_doc`
  - Test `open_pr`
- [ ] Achieve >80% code coverage
- [ ] Set up coverage reporting

### Acceptance Criteria
- All functions have unit tests
- Test coverage >80%
- Tests run via `make test` (with pytest markers for unit tests)
- Tests are fast and isolated

---

## Issue 10: Integration Test Suite

**Priority:** Medium  
**Estimated Effort:** 6-8 hours

### Description
Create integration tests that test MCP servers end-to-end.

### Tasks
- [ ] Set up integration test framework:
  - Test containers
  - Mock external services
  - Test data setup/teardown
- [ ] Create integration tests for:
  - MCP protocol communication
  - Server-to-server communication
  - File system operations
  - Git operations (with test repos)
  - API operations (with mock APIs)
- [ ] Set up test fixtures for integration tests
- [ ] Document integration test setup

### Acceptance Criteria
- Integration tests verify end-to-end workflows
- Tests can run in CI-like environment
- Tests are isolated and repeatable
- Tests run via `make test` (with pytest markers for integration tests)

---

## Issue 11: Linting and Code Quality

**Priority:** Medium  
**Estimated Effort:** 3-4 hours

### Description
Set up linting and code quality tools.

### Tasks
- [ ] Configure `black` for code formatting:
  - Set line length (88 or 100)
  - Configure in `pyproject.toml`
- [ ] Configure `ruff` for linting:
  - Enable appropriate rule sets
  - Configure in `pyproject.toml`
- [ ] Configure `mypy` for type checking:
  - Set strictness level
  - Configure in `pyproject.toml`
- [ ] Add pre-commit hooks (optional, but recommended)
- [ ] Ensure all code passes linting
- [ ] Document linting standards

### Acceptance Criteria
- `make lint` runs all linters (black, ruff, mypy) and checks formatting
- Code can be formatted with `black .` directly or via lint check
- All code passes type checking (included in `make lint`)
- Linting standards are documented

---

## Issue 12: Documentation

**Priority:** Medium  
**Estimated Effort:** 4-5 hours

### Description
Create comprehensive documentation for the project.

### Tasks
- [ ] Update `README.md` with:
  - Project overview
  - Quick start guide
  - Installation instructions
  - Usage examples
  - Configuration guide
- [ ] Create `docs/API.md` documenting:
  - MCP server APIs
  - Function signatures
  - Request/response formats
- [ ] Create `docs/DEPLOYMENT.md` documenting:
  - Podman container deployment
  - Environment variables
  - Configuration options
  - Rootless Podman setup
- [ ] Create `docs/DEVELOPMENT.md` documenting:
  - Development setup
  - Running tests
  - Contributing guidelines
- [ ] Add docstrings to all public functions
- [ ] Create example configuration files

### Acceptance Criteria
- All documentation is complete and accurate
- Examples work as documented
- API documentation is comprehensive
- Development guide is clear

---

## Issue 13: Error Handling and Resilience

**Priority:** Medium  
**Estimated Effort:** 4-5 hours

### Description
Implement robust error handling across all MCP servers.

### Tasks
- [ ] Define error types and exceptions:
  - Custom exception classes
  - Error codes
  - Error messages
- [ ] Implement error handling:
  - Try-catch blocks
  - Error logging
  - User-friendly error messages
- [ ] Add retry logic for external API calls
- [ ] Add timeout handling
- [ ] Add validation for all inputs
- [ ] Test error scenarios

### Acceptance Criteria
- All errors are caught and handled gracefully
- Error messages are informative
- External API failures don't crash servers
- Input validation prevents invalid requests

---

## Issue 14: Security Hardening

**Priority:** High  
**Estimated Effort:** 5-6 hours

### Description
Implement security best practices for the MCP servers.

### Tasks
- [ ] Secure credential storage:
  - Use environment variables for secrets
  - Never commit credentials
  - Use secure credential management
- [ ] Implement input validation:
  - Sanitize file paths
  - Validate feature IDs
  - Prevent path traversal attacks
- [ ] Add rate limiting (if needed)
- [ ] Secure API communication:
  - Use HTTPS
  - Validate certificates
- [ ] Review dependencies for vulnerabilities
- [ ] Document security considerations

### Acceptance Criteria
- No credentials in code or config files
- Input validation prevents attacks
- Dependencies are up-to-date
- Security best practices are followed

---

## Issue 15: Performance Optimization

**Priority:** Low  
**Estimated Effort:** 4-6 hours

### Description
Optimize performance of MCP servers.

### Tasks
- [ ] Profile server performance
- [ ] Optimize slow operations:
  - Cache templates
  - Optimize file I/O
  - Optimize git operations
- [ ] Add connection pooling for external APIs
- [ ] Implement async operations where appropriate
- [ ] Add performance metrics
- [ ] Document performance characteristics

### Acceptance Criteria
- Servers respond quickly (<1s for most operations)
- Caching reduces redundant operations
- Performance metrics are collected
- Performance is documented

---

## Issue 16: Default Templates (Package Resources)

**Priority:** Medium  
**Estimated Effort:** 3-4 hours

### Description
Create the actual content for the default templates that will be bundled with the MCP servers (Layer 1).

### Tasks
- [ ] Create content for default templates (to be stored in `src/templates_style_server/defaults/templates/`):
  - Concept template (Jinja2)
  - Task/How-To template (Jinja2)
  - API Reference template (Jinja2)
  - Release Notes template (Jinja2)
  - Feature Overview template (Jinja2)
  - Configuration Reference template (Jinja2)
- [ ] Document template structure and variables
- [ ] Verify templates work with the template engine

### Acceptance Criteria
- All doc types have high-quality default templates
- Templates follow the default style guide
- Content is correctly placed in the source tree for bundling

---

## Issue 17: End-to-End Testing

**Priority:** Medium  
**Estimated Effort:** 6-8 hours

### Description
Create end-to-end tests that simulate real-world usage scenarios.

### Tasks
- [ ] Create test scenarios:
  - Generate docs from code repo (same-repo)
  - Generate docs from code repo (external-repo)
  - Update existing documentation
  - Handle errors gracefully
- [ ] Set up test environment:
  - Mock repositories
  - Mock external services
  - Test data
- [ ] Implement E2E tests
- [ ] Document E2E test scenarios

### Acceptance Criteria
- E2E tests cover main workflows
- Tests are repeatable
- Tests verify complete documentation generation flow
- Tests run via `make test`

---

## Implementation Order Recommendation

1. **Phase 1: Foundation** (Issues 1-3)
   - Project setup, Makefile, Podman

2. **Phase 2: Core Servers** (Issues 4-6)
   - Implement all three MCP servers

3. **Phase 3: Quality & Infrastructure** (Issues 7-11)
   - Configuration, logging, testing, linting

4. **Phase 4: Polish** (Issues 12-17)
   - Documentation, error handling, security, performance

---

## Notes

- All MCP servers should follow the MCP protocol specification
- Use Python 3.11+ for modern features
- Prefer async/await for I/O operations
- Use type hints throughout
- Follow PEP 8 style guidelines
- No GitHub Actions - all CI/CD should be manual via Makefile

