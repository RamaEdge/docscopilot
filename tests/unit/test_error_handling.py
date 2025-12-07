"""Tests for error handling and resilience."""

import pytest
import requests

from src.shared.errors import (
    APIError,
    ErrorCode,
    GitTimeoutError,
    InvalidPathError,
    ValidationError,
)
from src.shared.retry import retry_with_backoff
from src.shared.validation import (
    validate_branch_name,
    validate_doc_type,
    validate_feature_id,
    validate_path,
)


@pytest.mark.unit
class TestErrorCodes:
    """Test error code functionality."""

    def test_error_to_dict(self):
        """Test error to_dict method."""
        error = ValidationError("Test error", "Test details")
        error_dict = error.to_dict()

        assert error_dict["error"] == "ValidationError"
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert error_dict["details"] == "Test details"

    def test_error_code_enum(self):
        """Test error code enum values."""
        assert ErrorCode.REPOSITORY_NOT_FOUND.value == "REPO_1001"
        assert ErrorCode.API_TIMEOUT.value == "API_6002"
        assert ErrorCode.VALIDATION_ERROR.value == "VALID_7001"


@pytest.mark.unit
class TestInputValidation:
    """Test input validation functions."""

    def test_validate_feature_id_valid(self):
        """Test validating valid feature IDs."""
        assert validate_feature_id("TEST-123") == "TEST-123"
        assert validate_feature_id("feature/name") == "feature/name"
        assert validate_feature_id("feature_name") == "feature_name"

    def test_validate_feature_id_empty(self):
        """Test validating empty feature ID."""
        with pytest.raises(ValidationError) as exc_info:
            validate_feature_id("")
        assert exc_info.value.error_code == ErrorCode.VALIDATION_ERROR

    def test_validate_feature_id_invalid_chars(self):
        """Test validating feature ID with invalid characters."""
        with pytest.raises(ValidationError) as exc_info:
            validate_feature_id("test@123")
        # Check that validation error is raised with appropriate message
        assert exc_info.value.error_code == ErrorCode.VALIDATION_ERROR
        assert (
            "invalid" in exc_info.value.message.lower()
            or "format" in exc_info.value.message.lower()
            or "alphanumeric" in exc_info.value.details.lower()
        )

    def test_validate_feature_id_too_long(self):
        """Test validating feature ID that's too long."""
        long_id = "a" * 201
        with pytest.raises(ValidationError) as exc_info:
            validate_feature_id(long_id)
        assert "too long" in exc_info.value.message.lower()

    def test_validate_doc_type_valid(self):
        """Test validating valid document types."""
        assert validate_doc_type("concept") == "concept"
        assert validate_doc_type("task") == "task"
        assert validate_doc_type("api_reference") == "api_reference"

    def test_validate_doc_type_default(self):
        """Test validating None doc_type returns default."""
        assert validate_doc_type(None) == "concept"

    def test_validate_doc_type_invalid(self):
        """Test validating invalid document type."""
        with pytest.raises(ValidationError) as exc_info:
            validate_doc_type("invalid_type")
        assert "invalid" in exc_info.value.message.lower()

    def test_validate_branch_name_valid(self):
        """Test validating valid branch names."""
        assert validate_branch_name("feature-branch") == "feature-branch"
        assert validate_branch_name("fix/bug-123") == "fix/bug-123"

    def test_validate_branch_name_invalid(self):
        """Test validating invalid branch names."""
        with pytest.raises(ValidationError) as exc_info:
            validate_branch_name("branch..name")
        assert "invalid" in exc_info.value.message.lower()
        assert exc_info.value.error_code == ErrorCode.VALIDATION_ERROR

        with pytest.raises(ValidationError) as exc_info2:
            validate_branch_name(".branch")
        assert "invalid" in exc_info2.value.message.lower()
        assert exc_info2.value.error_code == ErrorCode.VALIDATION_ERROR

    def test_validate_path_valid(self, tmp_path):
        """Test validating valid paths."""
        test_file = tmp_path / "test.md"
        test_file.write_text("test")
        result = validate_path("test.md", tmp_path)
        assert result == test_file

    def test_validate_path_outside_workspace(self, tmp_path):
        """Test validating path outside workspace."""
        with pytest.raises(InvalidPathError) as exc_info:
            validate_path("/etc/passwd", tmp_path)
        assert "outside workspace" in exc_info.value.message.lower()

    def test_validate_path_traversal(self, tmp_path):
        """Test validating path with traversal."""
        with pytest.raises(InvalidPathError) as exc_info:
            validate_path("../../etc/passwd", tmp_path)
        assert "invalid" in exc_info.value.message.lower()


@pytest.mark.unit
class TestRetryLogic:
    """Test retry logic for API calls."""

    def test_retry_success_first_attempt(self):
        """Test retry succeeds on first attempt."""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self):
        """Test retry succeeds after some failures."""
        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise requests.RequestException("Temporary failure")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 2

    def test_retry_exhausted(self):
        """Test retry exhausts all attempts."""
        call_count = 0

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise requests.RequestException("Persistent failure")

        with pytest.raises(APIError) as exc_info:
            test_func()

        assert call_count == 3  # Initial + 2 retries
        assert exc_info.value.error_code == ErrorCode.API_REQUEST_FAILED

    def test_retry_only_retryable_exceptions(self):
        """Test retry only retries specified exceptions."""
        call_count = 0

        @retry_with_backoff(
            max_retries=2,
            initial_delay=0.01,
            retryable_exceptions=(requests.RequestException,),
        )
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")

        with pytest.raises(ValueError):
            test_func()

        assert call_count == 1  # Should not retry


@pytest.mark.unit
class TestTimeoutHandling:
    """Test timeout handling."""

    def test_git_timeout_error(self):
        """Test GitTimeoutError creation."""
        error = GitTimeoutError("Command timed out", "Details")
        assert error.error_code == ErrorCode.GIT_TIMEOUT
        assert error.message == "Command timed out"
        assert error.details == "Details"
