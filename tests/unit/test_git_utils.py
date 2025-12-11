"""Unit tests for git_utils module."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.shared.errors import GitCommandError, RepositoryNotFoundError
from src.shared.git_utils import GitUtils


@pytest.mark.unit
class TestGitUtils:
    """Test cases for GitUtils class."""

    def test_init(self, tmp_path):
        """Test GitUtils initialization."""
        git_utils = GitUtils(tmp_path, "git")
        assert git_utils.workspace_root == tmp_path
        assert git_utils.git_binary == "git"

    def test_run_git_command_repo_not_found(self, tmp_path):
        """Test git command with non-existent repository."""
        git_utils = GitUtils(tmp_path)
        non_existent = tmp_path / "nonexistent"

        with pytest.raises(RepositoryNotFoundError):
            git_utils._run_git_command(non_existent, "status")

    def test_run_git_command_not_git_repo(self, tmp_path):
        """Test git command with non-git directory."""
        git_utils = GitUtils(tmp_path)
        regular_dir = tmp_path / "regular"
        regular_dir.mkdir()

        with pytest.raises(RepositoryNotFoundError):
            git_utils._run_git_command(regular_dir, "status")

    @patch("subprocess.run")
    def test_run_git_command_success(self, mock_run, tmp_path):
        """Test successful git command execution."""
        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        git_utils = GitUtils(tmp_path)
        # Create a mock git repo
        (tmp_path / ".git").mkdir()

        result = git_utils._run_git_command(tmp_path, "status")
        assert result == "output"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_run_git_command_failure(self, mock_run, tmp_path):
        """Test git command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git", stderr="error")

        git_utils = GitUtils(tmp_path)
        (tmp_path / ".git").mkdir()

        with pytest.raises(GitCommandError):
            git_utils._run_git_command(tmp_path, "status")

    @patch("subprocess.run")
    def test_log_grep(self, mock_run, tmp_path):
        """Test log_grep method."""
        mock_result = MagicMock()
        mock_result.stdout = "abc1234\ndef4567\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        git_utils = GitUtils(tmp_path)
        (tmp_path / ".git").mkdir()

        result = git_utils.log_grep(tmp_path, "feature-123")
        assert result == ["abc1234", "def4567"]

    @patch("subprocess.run")
    def test_get_commit_info(self, mock_run, tmp_path):
        """Test get_commit_info method."""
        mock_result = MagicMock()
        mock_result.stdout = "abc1234|Subject|Body"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        git_utils = GitUtils(tmp_path)
        (tmp_path / ".git").mkdir()

        commit_hash = "abc1234"
        result = git_utils.get_commit_info(tmp_path, commit_hash)
        assert result["hash"] == "abc1234"
        assert result["subject"] == "Subject"
        assert result["body"] == "Body"

    @patch("subprocess.run")
    def test_get_branches_containing(self, mock_run, tmp_path):
        """Test get_branches_containing method."""
        mock_result = MagicMock()
        mock_result.stdout = "  main\n* feature\n  remotes/origin/main"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        git_utils = GitUtils(tmp_path)
        (tmp_path / ".git").mkdir()

        commit_hash = "abc1234"
        result = git_utils.get_branches_containing(tmp_path, commit_hash)
        assert "main" in result
        assert "feature" in result
        assert "origin/main" in result

    @patch("subprocess.run")
    def test_get_tags_containing(self, mock_run, tmp_path):
        """Test get_tags_containing method."""
        mock_result = MagicMock()
        mock_result.stdout = "v1.0.0\nv1.1.0\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        git_utils = GitUtils(tmp_path)
        (tmp_path / ".git").mkdir()

        commit_hash = "abc1234"
        result = git_utils.get_tags_containing(tmp_path, commit_hash)
        assert result == ["v1.0.0", "v1.1.0"]

    @patch("subprocess.run")
    def test_diff_files(self, mock_run, tmp_path):
        """Test diff_files method."""
        mock_result = MagicMock()
        mock_result.stdout = "file1.py\nfile2.py\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        git_utils = GitUtils(tmp_path)
        (tmp_path / ".git").mkdir()

        # Use valid commit hashes
        base = "a" * 7
        head = "b" * 7
        result = git_utils.diff_files(tmp_path, base, head)
        assert result == ["file1.py", "file2.py"]

    @patch("subprocess.run")
    def test_ls_files(self, mock_run, tmp_path):
        """Test ls_files method."""
        mock_result = MagicMock()
        mock_result.stdout = "test_file1.py\ntest_file2.py\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        git_utils = GitUtils(tmp_path)
        (tmp_path / ".git").mkdir()

        result = git_utils.ls_files(tmp_path, "test_*.py")
        assert result == ["test_file1.py", "test_file2.py"]
