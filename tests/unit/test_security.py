"""Unit tests for security module."""

import pytest

from src.shared.security import SecurityError, SecurityValidator


@pytest.mark.unit
class TestSecurityValidator:
    """Test cases for SecurityValidator class."""

    def test_validate_feature_id_valid(self):
        """Test validating valid feature IDs."""
        assert SecurityValidator.validate_feature_id("feature-123") == "feature-123"
        assert SecurityValidator.validate_feature_id("FEATURE_123") == "FEATURE_123"
        assert SecurityValidator.validate_feature_id("feature/123") == "feature/123"
        assert SecurityValidator.validate_feature_id("a" * 200) == "a" * 200

    def test_validate_feature_id_invalid_characters(self):
        """Test validating feature IDs with invalid characters."""
        with pytest.raises(SecurityError):
            SecurityValidator.validate_feature_id("feature;123")
        with pytest.raises(SecurityError):
            SecurityValidator.validate_feature_id("feature&123")
        with pytest.raises(SecurityError):
            SecurityValidator.validate_feature_id("feature|123")

    def test_validate_feature_id_too_long(self):
        """Test validating feature IDs that are too long."""
        with pytest.raises(SecurityError):
            SecurityValidator.validate_feature_id("a" * 201)

    def test_validate_feature_id_empty(self):
        """Test validating empty feature ID."""
        with pytest.raises(SecurityError):
            SecurityValidator.validate_feature_id("")
        with pytest.raises(SecurityError):
            SecurityValidator.validate_feature_id("   ")

    def test_validate_feature_id_dangerous_patterns(self):
        """Test validating feature IDs with dangerous patterns."""
        with pytest.raises(SecurityError):
            SecurityValidator.validate_feature_id("feature..123")
        with pytest.raises(SecurityError):
            SecurityValidator.validate_feature_id("feature\x00123")
        with pytest.raises(SecurityError):
            SecurityValidator.validate_feature_id("feature\n123")

    def test_validate_branch_name_valid(self):
        """Test validating valid branch names."""
        assert (
            SecurityValidator.validate_branch_name("feature-branch") == "feature-branch"
        )
        assert (
            SecurityValidator.validate_branch_name("feature_branch") == "feature_branch"
        )
        assert (
            SecurityValidator.validate_branch_name("feature/branch") == "feature/branch"
        )

    def test_validate_branch_name_invalid(self):
        """Test validating invalid branch names."""
        with pytest.raises(SecurityError):
            SecurityValidator.validate_branch_name("feature..branch")
        with pytest.raises(SecurityError):
            SecurityValidator.validate_branch_name(".branch")
        with pytest.raises(SecurityError):
            SecurityValidator.validate_branch_name("branch.")
        with pytest.raises(SecurityError):
            SecurityValidator.validate_branch_name("branch.lock")
        with pytest.raises(SecurityError):
            SecurityValidator.validate_branch_name("branch@{")

    def test_validate_product_name_valid(self):
        """Test validating valid product names."""
        assert SecurityValidator.validate_product_name("product-name") == "product-name"
        assert SecurityValidator.validate_product_name("product_name") == "product_name"
        assert SecurityValidator.validate_product_name(None) is None

    def test_validate_product_name_invalid(self):
        """Test validating invalid product names."""
        with pytest.raises(SecurityError):
            SecurityValidator.validate_product_name("product/name")
        with pytest.raises(SecurityError):
            SecurityValidator.validate_product_name("product name")

    def test_validate_doc_type_valid(self):
        """Test validating valid document types."""
        assert SecurityValidator.validate_doc_type("concept") == "concept"
        assert SecurityValidator.validate_doc_type("task") == "task"
        assert SecurityValidator.validate_doc_type("api_reference") == "api_reference"

    def test_validate_doc_type_invalid(self):
        """Test validating invalid document types."""
        with pytest.raises(SecurityError):
            SecurityValidator.validate_doc_type("invalid_type")
        with pytest.raises(SecurityError):
            SecurityValidator.validate_doc_type("../../etc/passwd")

    def test_validate_path_valid(self, tmp_path):
        """Test validating valid paths."""
        file_path = tmp_path / "test.md"
        file_path.touch()
        validated = SecurityValidator.validate_path("test.md", tmp_path)
        assert validated == file_path.resolve()

    def test_validate_path_outside_workspace(self, tmp_path):
        """Test validating paths outside workspace."""
        with pytest.raises(SecurityError):
            SecurityValidator.validate_path("/tmp/outside.md", tmp_path)

    def test_validate_path_traversal(self, tmp_path):
        """Test validating paths with traversal attempts."""
        with pytest.raises(SecurityError):
            SecurityValidator.validate_path("../../etc/passwd", tmp_path)

    def test_sanitize_git_pattern_valid(self):
        """Test sanitizing valid git patterns."""
        assert SecurityValidator.sanitize_git_pattern("feature-123") == "feature-123"
        assert SecurityValidator.sanitize_git_pattern("TEST-456") == "TEST-456"

    def test_sanitize_git_pattern_injection(self):
        """Test sanitizing git patterns with injection attempts."""
        with pytest.raises(SecurityError):
            SecurityValidator.sanitize_git_pattern("feature;rm -rf /")
        with pytest.raises(SecurityError):
            SecurityValidator.sanitize_git_pattern("feature&command")
        with pytest.raises(SecurityError):
            SecurityValidator.sanitize_git_pattern("feature|command")
        with pytest.raises(SecurityError):
            SecurityValidator.sanitize_git_pattern("feature`command`")
        with pytest.raises(SecurityError):
            SecurityValidator.sanitize_git_pattern("feature$(command)")

    def test_sanitize_commit_hash_valid(self):
        """Test sanitizing valid commit hashes."""
        assert SecurityValidator.sanitize_commit_hash("abc1234") == "abc1234"
        assert SecurityValidator.sanitize_commit_hash("a" * 40) == "a" * 40

    def test_sanitize_commit_hash_invalid(self):
        """Test sanitizing invalid commit hashes."""
        with pytest.raises(SecurityError):
            SecurityValidator.sanitize_commit_hash("abc123")  # Too short
        with pytest.raises(SecurityError):
            SecurityValidator.sanitize_commit_hash("g" * 7)  # Invalid hex
        with pytest.raises(SecurityError):
            SecurityValidator.sanitize_commit_hash("abc12345;rm -rf")
