# Integration Test Suite

This document describes the integration test suite for DocsCopilot MCP servers.

## Overview

Integration tests verify end-to-end workflows of MCP servers, including:
- MCP protocol communication
- File system operations
- Git operations (with test repositories)
- API operations (with mocked external services)

## Test Structure

Integration tests are located in `tests/integration/` and are marked with the `@pytest.mark.integration` decorator.

### Test Files

- `test_code_context_server_integration.py`: Tests for Code Context MCP Server
- `test_templates_style_server_integration.py`: Tests for Templates + Style MCP Server
- `test_docs_repo_server_integration.py`: Tests for Docs Repo MCP Server
- `conftest.py`: Shared fixtures and test utilities

## Test Fixtures

### `temp_workspace`

Creates a temporary workspace directory that is automatically cleaned up after tests.

### `mock_git_repo`

Creates a real git repository in the temporary workspace with:
- Initialized git repository
- Configured git user (required for commits)
- Initial commit with README.md

### `mock_git_commands`

Mocks git command execution via `subprocess.run`. Use this when you need to control git command behavior without actually running git.

### `mock_github_api`

Mocks GitHub API requests (`requests.post`). Returns a successful PR creation response by default.

### `mock_gitlab_api`

Mocks GitLab API requests (`requests.post`). Returns a successful MR creation response by default.

### `mock_requests`

Mocks all HTTP requests. Use this for comprehensive request mocking.

## Running Integration Tests

### Run all integration tests

```bash
make test-integration
```

Or using pytest directly:

```bash
pytest -m integration
```

### Run specific integration test file

```bash
pytest tests/integration/test_code_context_server_integration.py
```

### Run all tests (unit + integration)

```bash
make test
```

## Test Isolation

Integration tests are designed to be isolated and repeatable:

1. **Temporary Workspaces**: Each test uses a temporary directory that is cleaned up automatically
2. **Mocked External Services**: All external services (GitHub API, GitLab API) are mocked
3. **Real File Systems**: Tests use real file system operations to verify actual behavior
4. **Real Git Repositories**: Tests create real git repositories but operate in isolated temporary directories

## External Service Mocking

### Git Operations

Git operations are tested using real git repositories in temporary directories. For tests that need to control git behavior, use the `mock_git_commands` fixture.

### GitHub API

GitHub API calls are mocked using the `mock_github_api` fixture. The fixture provides a default successful response, but you can customize it:

```python
def test_custom_github_response(mock_github_api):
    mock_response = MagicMock()
    mock_response.json.return_value = {"html_url": "...", "number": 123}
    mock_github_api.return_value = mock_response
    # Your test code
```

### GitLab API

GitLab API calls are mocked using the `mock_gitlab_api` fixture, similar to GitHub.

## Writing New Integration Tests

### Example: Testing File Operations

```python
@pytest.mark.integration
async def test_file_operation(temp_workspace: Path):
    """Test file operation with real file system."""
    test_file = temp_workspace / "test.txt"
    test_file.write_text("test content")
    
    # Your test code that uses the file
    assert test_file.exists()
    assert test_file.read_text() == "test content"
```

### Example: Testing Git Operations

```python
@pytest.mark.integration
async def test_git_operation(mock_git_repo: Path):
    """Test git operation with real repository."""
    # Create a commit
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "Test commit"],
        cwd=str(mock_git_repo),
        check=True,
    )
    
    # Your test code that uses git
```

### Example: Testing with Mocked APIs

```python
@pytest.mark.integration
async def test_api_operation(mock_github_api: MagicMock):
    """Test API operation with mocked service."""
    # Customize mock response if needed
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 123}
    mock_github_api.return_value = mock_response
    
    # Your test code that calls the API
```

## CI Integration

Integration tests are designed to run in CI-like environments:

- No external dependencies required (all services are mocked)
- Tests run in isolated temporary directories
- No network access required
- Fast execution (no real API calls)

## Troubleshooting

### Tests Fail Due to Git Configuration

Ensure git user is configured. The `mock_git_repo` fixture handles this automatically, but if you create your own git repos, configure:

```python
subprocess.run(["git", "config", "user.name", "Test User"], check=True)
subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
```

### Tests Fail Due to File Permissions

Integration tests use temporary directories that should have write permissions. If you encounter permission errors, check that the test is using `temp_workspace` or `mock_git_repo` fixtures.

### Mock Not Working

Ensure you're patching at the correct location. Use the full module path:

```python
with patch("src.docs_repo_server.server.repo_manager") as mock:
    # Your test
```

## Best Practices

1. **Use Real File Systems**: Prefer real file operations over mocks when testing file system behavior
2. **Mock External Services**: Always mock external APIs (GitHub, GitLab) to ensure tests are fast and isolated
3. **Clean Up**: Use fixtures that automatically clean up (like `temp_workspace`) rather than manual cleanup
4. **Test End-to-End**: Integration tests should verify complete workflows, not just individual functions
5. **Isolate Tests**: Each test should be independent and not rely on state from other tests
