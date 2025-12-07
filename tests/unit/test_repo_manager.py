"""Unit tests for repo_manager module."""

from unittest.mock import MagicMock, patch

import pytest

from src.docs_repo_server.repo_manager import RepoManager
from src.shared.config import DocsRepoConfig
from src.shared.errors import GitCommandError, InvalidPathError


class TestRepoManager:
    """Test cases for RepoManager class."""

    def test_init(self, tmp_path):
        """Test RepoManager initialization."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)
        assert manager.config == config
        assert manager.workspace_root == tmp_path
        assert manager.repo_mode == "same"

    def test_suggest_doc_location_concept(self, tmp_path):
        """Test suggesting doc location for concept."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        path, doc_type = manager.suggest_doc_location("feature-123", "concept")
        assert doc_type == "concept"
        assert "concepts" in path
        assert "feature-123" in path

    def test_suggest_doc_location_api_reference(self, tmp_path):
        """Test suggesting doc location for API reference."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        path, doc_type = manager.suggest_doc_location("api-endpoint", "api_reference")
        assert doc_type == "api_reference"
        assert "api" in path

    def test_suggest_doc_location_default_type(self, tmp_path):
        """Test suggesting doc location with default type."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        path, doc_type = manager.suggest_doc_location("feature-123")
        assert doc_type == "concept"
        assert path.endswith(".md")

    def test_write_doc_success(self, tmp_path):
        """Test successful document write."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        content = "# Test Document\n\nContent here"
        path, success, message = manager.write_doc("docs/test.md", content)

        assert success is True
        assert "test.md" in path
        assert (tmp_path / "docs" / "test.md").exists()
        assert (tmp_path / "docs" / "test.md").read_text() == content

    def test_write_doc_creates_directories(self, tmp_path):
        """Test that write_doc creates directory structure."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        content = "# Test"
        path, success, _ = manager.write_doc("docs/subdir/test.md", content)

        assert success is True
        assert (tmp_path / "docs" / "subdir" / "test.md").exists()

    def test_write_doc_path_outside_workspace(self, tmp_path):
        """Test write_doc with path outside workspace."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        with pytest.raises(InvalidPathError):
            manager.write_doc("/tmp/outside.md", "content")

    def test_write_doc_invalid_path(self, tmp_path):
        """Test write_doc with invalid path."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        with pytest.raises(InvalidPathError):
            manager.write_doc("../../etc/passwd", "content")

    @patch("src.docs_repo_server.repo_manager.GitUtils")
    def test_create_branch_success(self, mock_git_utils_class, tmp_path):
        """Test successful branch creation."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        mock_git_utils_instance = manager.git_utils
        mock_git_utils_instance._run_git_command = MagicMock(return_value="")

        success = manager.create_branch("feature-branch")
        assert success is True

    @patch("src.docs_repo_server.repo_manager.GitUtils")
    def test_create_branch_failure(self, mock_git_utils_class, tmp_path):
        """Test branch creation failure."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        mock_git_utils_instance = manager.git_utils
        mock_git_utils_instance._run_git_command = MagicMock(
            side_effect=GitCommandError("Failed", "Details")
        )

        success = manager.create_branch("feature-branch")
        assert success is False

    def test_commit_changes_success(self, tmp_path):
        """Test successful commit."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        manager.git_utils._run_git_command = MagicMock(return_value="")

        success = manager.commit_changes("Test commit")
        assert success is True

    def test_push_branch_success(self, tmp_path):
        """Test successful branch push."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        manager.git_utils._run_git_command = MagicMock(return_value="")

        success = manager.push_branch("feature-branch")
        assert success is True

    @patch("requests.post")
    def test_create_github_pr_success(self, mock_post, tmp_path):
        """Test successful GitHub PR creation."""
        config = DocsRepoConfig(workspace_root=tmp_path, github_token="test_token")
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        # Mock git remote URL
        manager.git_utils._run_git_command = MagicMock(
            return_value="git@github.com:owner/repo.git"
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "html_url": "https://github.com/owner/repo/pull/123",
            "number": 123,
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        pr_url, pr_number, success, message = manager.create_github_pr(
            "feature-branch", "Test PR", "Description"
        )

        assert success is True
        assert pr_url == "https://github.com/owner/repo/pull/123"
        assert pr_number == 123

    def test_create_github_pr_no_token(self, tmp_path):
        """Test GitHub PR creation without token."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        pr_url, pr_number, success, message = manager.create_github_pr(
            "branch", "Title", "Description"
        )

        assert success is False
        assert "token" in message.lower()

    @patch("requests.post")
    def test_create_gitlab_pr_success(self, mock_post, tmp_path):
        """Test successful GitLab MR creation."""
        config = DocsRepoConfig(workspace_root=tmp_path, gitlab_token="test_token")
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        # Mock git remote URL
        manager.git_utils._run_git_command = MagicMock(
            return_value="git@gitlab.com:owner/repo.git"
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "web_url": "https://gitlab.com/owner/repo/-/merge_requests/456",
            "iid": 456,
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        mr_url, mr_number, success, message = manager.create_gitlab_pr(
            "feature-branch", "Test MR", "Description"
        )

        assert success is True
        assert "gitlab.com" in mr_url
        assert mr_number == 456

    def test_parse_github_repo_ssh(self, tmp_path):
        """Test parsing GitHub repo from SSH URL."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        repo_info = manager._parse_github_repo("git@github.com:owner/repo.git")
        assert repo_info == ("owner", "repo")

    def test_parse_github_repo_https(self, tmp_path):
        """Test parsing GitHub repo from HTTPS URL."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        repo_info = manager._parse_github_repo("https://github.com/owner/repo.git")
        assert repo_info == ("owner", "repo")

    def test_parse_gitlab_repo_ssh(self, tmp_path):
        """Test parsing GitLab repo from SSH URL."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        project_id = manager._parse_gitlab_repo("git@gitlab.com:owner/repo.git")
        assert project_id == "owner%2Frepo"
