"""Unit tests for feature_metadata module."""

from unittest.mock import patch

import pytest

from src.code_context_server.feature_metadata import FeatureMetadataExtractor
from src.shared.errors import FeatureNotFoundError
from src.shared.git_utils import GitUtils


class TestFeatureMetadataExtractor:
    """Test cases for FeatureMetadataExtractor class."""

    def test_init(self, tmp_path):
        """Test FeatureMetadataExtractor initialization."""
        git_utils = GitUtils(tmp_path)
        extractor = FeatureMetadataExtractor(git_utils, tmp_path)
        assert extractor.git_utils == git_utils
        assert extractor.workspace_root == tmp_path

    @patch.object(GitUtils, "log_grep")
    def test_get_feature_metadata_not_found(self, mock_log_grep, tmp_path):
        """Test getting metadata for non-existent feature."""
        mock_log_grep.return_value = []
        git_utils = GitUtils(tmp_path)
        extractor = FeatureMetadataExtractor(git_utils, tmp_path)
        (tmp_path / ".git").mkdir()

        with pytest.raises(FeatureNotFoundError):
            extractor.get_feature_metadata("nonexistent-feature", tmp_path)

    @patch.object(GitUtils, "get_commit_info")
    @patch.object(GitUtils, "log_grep")
    def test_get_feature_metadata_success(
        self, mock_log_grep, mock_get_commit_info, tmp_path
    ):
        """Test successful feature metadata extraction."""
        mock_log_grep.return_value = ["abc123"]
        mock_get_commit_info.return_value = {
            "hash": "abc123",
            "subject": "Add feature-123",
            "body": "Fixes #456",
        }

        git_utils = GitUtils(tmp_path)
        extractor = FeatureMetadataExtractor(git_utils, tmp_path)
        (tmp_path / ".git").mkdir()

        metadata = extractor.get_feature_metadata("feature-123", tmp_path)
        assert metadata.feature_id == "feature-123"
        assert len(metadata.commits) == 1
        assert metadata.commits[0].hash == "abc123"

    @patch.object(GitUtils, "ls_files")
    @patch.object(GitUtils, "log_files")
    @patch.object(GitUtils, "get_tags_containing")
    @patch.object(GitUtils, "get_branches_containing")
    @patch.object(GitUtils, "get_commit_info")
    @patch.object(GitUtils, "log_grep")
    def test_get_feature_metadata_with_branches_tags(
        self,
        mock_log_grep,
        mock_get_commit_info,
        mock_get_branches,
        mock_get_tags,
        mock_log_files,
        mock_ls_files,
        tmp_path,
    ):
        """Test feature metadata with branches and tags."""
        mock_log_grep.return_value = ["abc123"]
        mock_get_commit_info.return_value = {
            "hash": "abc123",
            "subject": "Add feature",
            "body": "",
        }
        mock_get_branches.return_value = ["feature-branch", "main"]
        mock_get_tags.return_value = ["v1.0.0"]
        mock_log_files.return_value = ["src/file.py"]
        mock_ls_files.return_value = []  # No test files found

        git_utils = GitUtils(tmp_path)
        extractor = FeatureMetadataExtractor(git_utils, tmp_path)
        (tmp_path / ".git").mkdir()

        metadata = extractor.get_feature_metadata("feature-123", tmp_path)
        assert "feature-branch" in metadata.branches
        assert "v1.0.0" in metadata.tags
        assert "src/file.py" in metadata.code_paths
