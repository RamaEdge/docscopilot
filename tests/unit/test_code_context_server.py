"""Unit tests for code_context_server module."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.code_context_server import server
from src.code_context_server.server import app
from src.shared.errors import (
    DocsCopilotError,
    FeatureNotFoundError,
    FileNotFoundError,
    GitCommandError,
    RepositoryNotFoundError,
)


@pytest.mark.unit
class TestCodeContextServer:
    """Test cases for Code Context MCP Server."""

    def test_list_tools_decorator(self):
        """Test that list_tools decorator is registered."""
        # Check that the app exists and is configured
        assert app is not None
        assert hasattr(app, "name")
        assert app.name == "code-context-server"

    def test_list_tools(self):
        """Test listing available tools."""

        async def run_test():
            tools = await server.list_tools()
            assert len(tools) == 3
            tool_names = [tool.name for tool in tools]
            assert "get_feature_metadata" in tool_names
            assert "get_code_examples" in tool_names
            assert "get_changed_endpoints" in tool_names

        asyncio.run(run_test())

    @patch("src.code_context_server.server.feature_extractor")
    def test_call_tool_get_feature_metadata(self, mock_extractor, tmp_path):
        """Test get_feature_metadata tool call."""
        mock_metadata = MagicMock()
        mock_metadata.model_dump_json.return_value = '{"feature_id": "test-123"}'
        mock_extractor.get_feature_metadata.return_value = mock_metadata

        # Mock config.workspace_root
        with patch("src.code_context_server.server.config") as mock_config:
            mock_config.workspace_root = tmp_path

            async def run_test():
                result = await server.call_tool(
                    "get_feature_metadata", {"feature_id": "test-123"}
                )
                assert len(result) == 1
                assert "test-123" in result[0].text
                mock_extractor.get_feature_metadata.assert_called_once()
                # Check that feature_id was validated
                call_args = mock_extractor.get_feature_metadata.call_args
                assert call_args[0][0] == "test-123"

            asyncio.run(run_test())

    @patch("src.code_context_server.server.feature_extractor")
    def test_call_tool_get_feature_metadata_with_repo_path(
        self, mock_extractor, tmp_path
    ):
        """Test get_feature_metadata tool call with repo_path."""
        mock_metadata = MagicMock()
        mock_metadata.model_dump_json.return_value = '{"feature_id": "test-123"}'
        mock_extractor.get_feature_metadata.return_value = mock_metadata

        # Create repo_path directory
        repo_path = tmp_path / "repo1"
        repo_path.mkdir()

        # Mock config.workspace_root
        with patch("src.code_context_server.server.config") as mock_config:
            mock_config.workspace_root = tmp_path

            async def run_test():
                result = await server.call_tool(
                    "get_feature_metadata",
                    {"feature_id": "test-123", "repo_path": "repo1"},
                )
                assert len(result) == 1
                mock_extractor.get_feature_metadata.assert_called_once()
                # Check that repo_path was validated and converted to Path
                call_args = mock_extractor.get_feature_metadata.call_args
                assert call_args[0][0] == "test-123"
                assert isinstance(call_args[0][1], Path)

            asyncio.run(run_test())

    @patch("src.code_context_server.server.feature_extractor")
    def test_call_tool_get_feature_metadata_missing_feature_id(self, mock_extractor):
        """Test get_feature_metadata tool call with missing feature_id."""

        async def run_test():
            result = await server.call_tool("get_feature_metadata", {})
            assert len(result) == 1
            assert "error" in result[0].text.lower()
            mock_extractor.get_feature_metadata.assert_not_called()

        asyncio.run(run_test())

    @patch("src.code_context_server.server.feature_extractor")
    def test_call_tool_security_error(self, mock_extractor, tmp_path):
        """Test call_tool with SecurityError."""
        # Mock config.workspace_root
        with patch("src.code_context_server.server.config") as mock_config:
            mock_config.workspace_root = tmp_path

            async def run_test():
                # Test with invalid feature_id that triggers SecurityError
                result = await server.call_tool(
                    "get_feature_metadata", {"feature_id": "feature;rm -rf /"}
                )
                assert len(result) == 1
                assert "error" in result[0].text.lower()
                assert "security" in result[0].text.lower()

            asyncio.run(run_test())

    @patch("src.code_context_server.server.feature_extractor")
    def test_call_tool_get_feature_metadata_not_found(self, mock_extractor, tmp_path):
        """Test get_feature_metadata tool call when feature not found."""
        mock_extractor.get_feature_metadata.side_effect = FeatureNotFoundError(
            "Feature not found", "Details"
        )

        # Mock config.workspace_root
        with patch("src.code_context_server.server.config") as mock_config:
            mock_config.workspace_root = tmp_path

            async def run_test():
                result = await server.call_tool(
                    "get_feature_metadata", {"feature_id": "nonexistent"}
                )
                assert len(result) == 1
                assert "error" in result[0].text.lower()
                assert "feature not found" in result[0].text.lower()

            asyncio.run(run_test())

    @patch("src.code_context_server.server.code_examples_extractor")
    def test_call_tool_get_code_examples(self, mock_extractor, tmp_path):
        """Test get_code_examples tool call."""
        mock_examples = MagicMock()
        mock_examples.model_dump_json.return_value = (
            '{"path": "test.py", "examples": []}'
        )
        mock_extractor.get_code_examples.return_value = mock_examples

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.touch()

        # Mock config.workspace_root
        with patch("src.code_context_server.server.config") as mock_config:
            mock_config.workspace_root = tmp_path

            async def run_test():
                result = await server.call_tool(
                    "get_code_examples", {"path": "test.py"}
                )
                assert len(result) == 1
                assert "test.py" in result[0].text
                mock_extractor.get_code_examples.assert_called_once()

            asyncio.run(run_test())

    @patch("src.code_context_server.server.code_examples_extractor")
    def test_call_tool_get_code_examples_missing_path(self, mock_extractor):
        """Test get_code_examples tool call with missing path."""

        async def run_test():
            result = await server.call_tool("get_code_examples", {})
            assert len(result) == 1
            assert "error" in result[0].text.lower()
            mock_extractor.get_code_examples.assert_not_called()

        asyncio.run(run_test())

    @patch("src.code_context_server.server.code_examples_extractor")
    def test_call_tool_get_code_examples_file_not_found(self, mock_extractor):
        """Test get_code_examples tool call when file not found."""
        mock_extractor.get_code_examples.side_effect = FileNotFoundError(
            "File not found", "Details"
        )

        async def run_test():
            result = await server.call_tool(
                "get_code_examples", {"path": "nonexistent.py"}
            )
            assert len(result) == 1
            assert "error" in result[0].text.lower()
            assert "file not found" in result[0].text.lower()

        asyncio.run(run_test())

    @patch("src.code_context_server.server.endpoints_extractor")
    def test_call_tool_get_changed_endpoints_with_diff(self, mock_extractor):
        """Test get_changed_endpoints tool call with diff."""
        mock_endpoints = MagicMock()
        mock_endpoints.model_dump_json.return_value = '{"endpoints": []}'
        mock_extractor.get_changed_endpoints.return_value = mock_endpoints

        async def run_test():
            result = await server.call_tool(
                "get_changed_endpoints", {"diff": "diff content"}
            )
            assert len(result) == 1
            mock_extractor.get_changed_endpoints.assert_called_once_with(
                "diff content", None, None, None
            )

        asyncio.run(run_test())

    @patch("src.code_context_server.server.endpoints_extractor")
    def test_call_tool_get_changed_endpoints_with_git_refs(
        self, mock_extractor, tmp_path
    ):
        """Test get_changed_endpoints tool call with git refs."""
        mock_endpoints = MagicMock()
        mock_endpoints.model_dump_json.return_value = '{"endpoints": []}'
        mock_extractor.get_changed_endpoints.return_value = mock_endpoints

        # Create repo_path directory
        repo_path = tmp_path / "repo1"
        repo_path.mkdir()

        # Mock config.workspace_root
        with patch("src.code_context_server.server.config") as mock_config:
            mock_config.workspace_root = tmp_path

            async def run_test():
                result = await server.call_tool(
                    "get_changed_endpoints",
                    {
                        "repo_path": "repo1",
                        "base": "a" * 7,  # Valid commit hash
                        "head": "b" * 7,  # Valid commit hash
                    },
                )
                assert len(result) == 1
                mock_extractor.get_changed_endpoints.assert_called_once()
                # Check that repo_path was validated and converted to Path
                call_args = mock_extractor.get_changed_endpoints.call_args
                assert call_args[0][0] is None
                assert isinstance(call_args[0][1], Path)
                assert call_args[0][2] == "a" * 7
                assert call_args[0][3] == "b" * 7

            asyncio.run(run_test())

    @patch("src.code_context_server.server.endpoints_extractor")
    def test_call_tool_get_changed_endpoints_git_error(self, mock_extractor):
        """Test get_changed_endpoints tool call with git error."""
        mock_extractor.get_changed_endpoints.side_effect = GitCommandError(
            "Git command failed", "Details"
        )

        async def run_test():
            result = await server.call_tool(
                "get_changed_endpoints", {"diff": "diff content"}
            )
            assert len(result) == 1
            assert "error" in result[0].text.lower()
            assert "GitCommandError" in result[0].text or "REPO_1002" in result[0].text

        asyncio.run(run_test())

    @patch("src.code_context_server.server.endpoints_extractor")
    def test_call_tool_get_changed_endpoints_repo_not_found(self, mock_extractor):
        """Test get_changed_endpoints tool call with repository not found."""
        mock_extractor.get_changed_endpoints.side_effect = RepositoryNotFoundError(
            "Repository not found", "Details"
        )

        async def run_test():
            result = await server.call_tool(
                "get_changed_endpoints", {"repo_path": "nonexistent"}
            )
            assert len(result) == 1
            assert "error" in result[0].text.lower()
            assert (
                "RepositoryNotFoundError" in result[0].text
                or "REPO_1001" in result[0].text
            )

        asyncio.run(run_test())

    @patch("src.code_context_server.server.feature_extractor")
    def test_call_tool_docscopilot_error(self, mock_extractor):
        """Test call_tool with DocsCopilotError."""
        mock_extractor.get_feature_metadata.side_effect = DocsCopilotError(
            "DocsCopilot error", "Details"
        )

        async def run_test():
            result = await server.call_tool(
                "get_feature_metadata", {"feature_id": "test-123"}
            )
            assert len(result) == 1
            assert "error" in result[0].text.lower()
            assert "docscopilot error" in result[0].text.lower()

        asyncio.run(run_test())

    @patch("src.code_context_server.server.feature_extractor")
    def test_call_tool_unexpected_error(self, mock_extractor):
        """Test call_tool with unexpected error."""
        mock_extractor.get_feature_metadata.side_effect = RuntimeError(
            "Unexpected error"
        )

        async def run_test():
            result = await server.call_tool(
                "get_feature_metadata", {"feature_id": "test-123"}
            )
            assert len(result) == 1
            assert "error" in result[0].text.lower()
            assert "unexpected error" in result[0].text.lower()

        asyncio.run(run_test())

    def test_call_tool_unknown_tool(self):
        """Test call_tool with unknown tool name."""

        async def run_test():
            result = await server.call_tool("unknown_tool", {})
            assert len(result) == 1
            assert "error" in result[0].text.lower()

        asyncio.run(run_test())

    def test_call_tool_none_arguments(self):
        """Test call_tool with None arguments."""

        async def run_test():
            result = await server.call_tool("get_feature_metadata", None)
            assert len(result) == 1
            assert "error" in result[0].text.lower()

        asyncio.run(run_test())
