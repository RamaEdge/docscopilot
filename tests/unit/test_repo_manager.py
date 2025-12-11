"""Unit tests for repo_manager module."""

from unittest.mock import MagicMock, patch

import pytest

from src.docs_repo_server.repo_manager import RepoManager
from src.shared.config import DocsRepoConfig
from src.shared.errors import GitCommandError


@pytest.mark.unit
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

        # Security validation will raise SecurityError, not InvalidPathError
        from src.shared.security import SecurityError

        with pytest.raises(SecurityError):
            manager.write_doc("/tmp/outside.md", "content")

    def test_write_doc_invalid_path(self, tmp_path):
        """Test write_doc with invalid path."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        # Security validation will raise SecurityError, not InvalidPathError
        from src.shared.security import SecurityError

        with pytest.raises(SecurityError):
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

    def test_create_github_pr_success(self, tmp_path):
        """Test successful GitHub PR creation."""
        config = DocsRepoConfig(workspace_root=tmp_path, github_token="test_token")
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        # Mock git remote URL
        manager.git_utils._run_git_command = MagicMock(
            return_value="git@github.com:owner/repo.git"
        )

        # Mock the session.post method
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "html_url": "https://github.com/owner/repo/pull/123",
            "number": 123,
        }
        mock_response.raise_for_status = MagicMock()
        manager.session.post = MagicMock(return_value=mock_response)

        pr_url, pr_number, success, message = manager.create_github_pr(
            "feature-branch", "Test PR", "Description"
        )

        assert success is True
        assert pr_url == "https://github.com/owner/repo/pull/123"
        assert pr_number == 123
        # Verify HTTPS and certificate verification
        manager.session.post.assert_called_once()
        call_kwargs = manager.session.post.call_args[1]
        assert call_kwargs.get("verify") is True

    def test_create_github_pr_no_token(self, tmp_path):
        """Test GitHub PR creation without token."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        pr_url, pr_number, success, message = manager.create_github_pr(
            "branch", "Title", "Description"
        )

        assert success is False
        assert "token" in message.lower()

    def test_create_gitlab_pr_success(self, tmp_path):
        """Test successful GitLab MR creation."""
        config = DocsRepoConfig(workspace_root=tmp_path, gitlab_token="test_token")
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        # Mock git remote URL
        manager.git_utils._run_git_command = MagicMock(
            return_value="git@gitlab.com:owner/repo.git"
        )

        # Mock the session.post method
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "web_url": "https://gitlab.com/owner/repo/-/merge_requests/456",
            "iid": 456,
        }
        mock_response.raise_for_status = MagicMock()
        manager.session.post = MagicMock(return_value=mock_response)

        mr_url, mr_number, success, message = manager.create_gitlab_pr(
            "feature-branch", "Test MR", "Description"
        )

        assert success is True
        assert "gitlab.com" in mr_url
        assert mr_number == 456
        # Verify HTTPS and certificate verification
        manager.session.post.assert_called_once()
        call_kwargs = manager.session.post.call_args[1]
        assert call_kwargs.get("verify") is True

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

    def test_generate_branch_name_from_title(self, tmp_path):
        """Test branch name generation from title."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        # Mock git command to return empty branches list
        manager.git_utils._run_git_command = MagicMock(return_value="")

        branch_name = manager.generate_branch_name(
            title="Add Documentation for Feature"
        )
        assert branch_name.startswith("docs/")
        assert "add-documentation-for-feature" in branch_name.lower()

    def test_generate_branch_name_from_feature_id(self, tmp_path):
        """Test branch name generation from feature_id."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        # Mock git command to return empty branches list
        manager.git_utils._run_git_command = MagicMock(return_value="")

        branch_name = manager.generate_branch_name(
            title="Add Documentation", feature_id="FEAT-123"
        )
        assert branch_name.startswith("docs/")
        assert "feat-123" in branch_name.lower()

    def test_generate_branch_name_sanitization(self, tmp_path):
        """Test branch name sanitization."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        manager.git_utils._run_git_command = MagicMock(return_value="")

        # Test with special characters
        branch_name = manager.generate_branch_name(title="Feature: Add API Docs!")
        assert ":" not in branch_name
        assert "!" not in branch_name
        assert branch_name.startswith("docs/")

    def test_generate_branch_name_ensures_unique(self, tmp_path):
        """Test branch name uniqueness checking."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        # Mock existing branch
        manager.git_utils._run_git_command = MagicMock(
            return_value="  main\n* docs/test-feature\n  remotes/origin/main"
        )

        branch_name = manager.generate_branch_name(
            title="Test Feature", ensure_unique=True
        )
        # Should append number if branch exists
        assert branch_name.startswith("docs/")
        # Should be unique (either original or with number suffix)

    def test_generate_branch_name_validates_git_rules(self, tmp_path):
        """Test that generated branch names follow Git rules."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)
        (tmp_path / ".git").mkdir()

        manager.git_utils._run_git_command = MagicMock(return_value="")

        # Test with title that would create invalid branch name
        branch_name = manager.generate_branch_name(title=".lock file update")
        assert not branch_name.endswith(".lock")
        assert not branch_name.startswith(".")

    def test_sanitize_for_branch(self, tmp_path):
        """Test _sanitize_for_branch helper method."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        # Test various inputs
        assert manager._sanitize_for_branch("Feature Name") == "feature-name"
        assert manager._sanitize_for_branch("FEAT_123") == "feat-123"
        assert manager._sanitize_for_branch("Feature/Name") == "feature-name"
        assert manager._sanitize_for_branch("Feature!!!") == "feature"
        assert manager._sanitize_for_branch("") == ""

    def test_ensure_valid_branch_name(self, tmp_path):
        """Test _ensure_valid_branch_name helper method."""
        config = DocsRepoConfig(workspace_root=tmp_path)
        manager = RepoManager(config)

        # Test Git rule violations
        assert manager._ensure_valid_branch_name(".branch") == "branch"
        assert manager._ensure_valid_branch_name("branch.") == "branch"
        assert manager._ensure_valid_branch_name("branch.lock") == "branch"
        # ".." gets replaced with "-"
        assert manager._ensure_valid_branch_name("branch..name") == "branch-name"
        # "@" and "{" get replaced with "-"
        result = manager._ensure_valid_branch_name("branch@{name}")
        assert result.startswith("branch")
        assert "@" not in result
        assert "{" not in result
