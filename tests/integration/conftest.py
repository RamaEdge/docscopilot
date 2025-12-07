"""Pytest fixtures for integration tests."""

import subprocess
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        yield workspace


@pytest.fixture
def mock_git_repo(temp_workspace: Path) -> Generator[Path, None, None]:
    """Create a mock git repository in temp workspace."""
    repo_path = temp_workspace / "test_repo"
    repo_path.mkdir(parents=True, exist_ok=True)

    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=str(repo_path),
        capture_output=True,
        check=True,
    )

    # Configure git user (required for commits)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(repo_path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(repo_path),
        capture_output=True,
        check=True,
    )

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repo\n")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=str(repo_path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(repo_path),
        capture_output=True,
        check=True,
    )

    yield repo_path


@pytest.fixture
def mock_git_commands():
    """Mock git command execution."""
    with patch("subprocess.run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_github_api():
    """Mock GitHub API requests."""
    with patch("requests.post") as mock_post:
        # Default successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "html_url": "https://github.com/owner/repo/pull/123",
            "number": 123,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_gitlab_api():
    """Mock GitLab API requests."""
    with patch("requests.post") as mock_post:
        # Default successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "web_url": "https://gitlab.com/owner/repo/-/merge_requests/456",
            "iid": 456,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_requests():
    """Mock all HTTP requests."""
    with patch("requests.post") as mock_post:
        yield mock_post
