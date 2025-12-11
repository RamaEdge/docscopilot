"""Unit tests for docs_repo_server module."""

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from src.docs_repo_server import server


@pytest.mark.unit
class TestDocsRepoServer:
    """Test cases for Docs Repo MCP Server."""

    def test_list_tools(self):
        """Test listing available tools."""

        async def run_test():
            tools = await server.list_tools()
            assert len(tools) == 3
            tool_names = [tool.name for tool in tools]
            assert "suggest_doc_location" in tool_names
            assert "write_doc" in tool_names
            assert "open_pr" in tool_names

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_suggest_doc_location(self, mock_manager):
        """Test suggest_doc_location tool call."""
        mock_manager.workspace_root = Path("/tmp")
        mock_manager.suggest_doc_location.return_value = (
            "docs/concepts/feature.md",
            "concept",
        )

        async def run_test():
            result = await server.call_tool(
                "suggest_doc_location", {"feature_id": "feature-123"}
            )
            assert len(result) == 1
            assert "feature.md" in result[0].text
            mock_manager.suggest_doc_location.assert_called_once_with(
                "feature-123", None  # doc_type not provided, defaults to None
            )

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_write_doc(self, mock_manager, tmp_path):
        """Test write_doc tool call."""
        mock_manager.workspace_root = tmp_path
        mock_manager.write_doc.return_value = (
            "docs/test.md",
            True,
            "Document written successfully",
        )

        async def run_test():
            result = await server.call_tool(
                "write_doc", {"path": "docs/test.md", "content": "# Test"}
            )
            assert len(result) == 1
            assert "test.md" in result[0].text
            mock_manager.write_doc.assert_called_once()

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_open_pr_success(self, mock_manager, tmp_path):
        """Test open_pr tool call success with provided branch."""
        mock_manager.workspace_root = tmp_path
        mock_manager.create_branch.return_value = True
        mock_manager.commit_changes.return_value = True
        mock_manager.push_branch.return_value = True
        mock_manager.create_github_pr.return_value = (
            "https://github.com/owner/repo/pull/123",
            123,
            True,
            "PR created",
        )

        async def run_test():
            result = await server.call_tool(
                "open_pr",
                {
                    "branch": "feature-branch",
                    "title": "Test PR",
                    "description": "Test description",
                },
            )
            assert len(result) == 1
            assert "pr" in result[0].text.lower() or "123" in result[0].text
            # Check that branch name was validated
            mock_manager.create_branch.assert_called_once_with("feature-branch")

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_open_pr_auto_generate_branch(self, mock_manager, tmp_path):
        """Test open_pr tool call with auto-generated branch name."""
        mock_manager.workspace_root = tmp_path
        mock_manager.generate_branch_name.return_value = "docs/test-pr"
        mock_manager.create_branch.return_value = True
        mock_manager.commit_changes.return_value = True
        mock_manager.push_branch.return_value = True
        mock_manager.create_github_pr.return_value = (
            "https://github.com/owner/repo/pull/123",
            123,
            True,
            "PR created",
        )

        async def run_test():
            result = await server.call_tool(
                "open_pr",
                {
                    "title": "Test PR",
                    "description": "Test description",
                },
            )
            assert len(result) == 1
            assert "pr" in result[0].text.lower() or "123" in result[0].text
            # Check that branch was auto-generated
            mock_manager.generate_branch_name.assert_called_once_with(
                title="Test PR", feature_id=None
            )
            mock_manager.create_branch.assert_called_once_with("docs/test-pr")

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_open_pr_auto_generate_with_feature_id(
        self, mock_manager, tmp_path
    ):
        """Test open_pr tool call with auto-generated branch using feature_id."""
        mock_manager.workspace_root = tmp_path
        mock_manager.generate_branch_name.return_value = "docs/feat-123"
        mock_manager.create_branch.return_value = True
        mock_manager.commit_changes.return_value = True
        mock_manager.push_branch.return_value = True
        mock_manager.create_github_pr.return_value = (
            "https://github.com/owner/repo/pull/123",
            123,
            True,
            "PR created",
        )

        async def run_test():
            result = await server.call_tool(
                "open_pr",
                {
                    "title": "Add documentation",
                    "description": "Test description",
                    "feature_id": "FEAT-123",
                },
            )
            assert len(result) == 1
            assert "pr" in result[0].text.lower() or "123" in result[0].text
            # Check that branch was auto-generated with feature_id
            mock_manager.generate_branch_name.assert_called_once_with(
                title="Add documentation", feature_id="FEAT-123"
            )
            mock_manager.create_branch.assert_called_once_with("docs/feat-123")

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_open_pr_branch_failure(self, mock_manager, tmp_path):
        """Test open_pr with branch creation failure."""
        mock_manager.workspace_root = tmp_path
        mock_manager.generate_branch_name.return_value = "docs/test-pr"
        mock_manager.create_branch.return_value = False

        async def run_test():
            result = await server.call_tool(
                "open_pr",
                {
                    "title": "Test PR",
                    "description": "Test description",
                },
            )
            assert len(result) == 1
            assert "error" in result[0].text.lower()

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_open_pr_gitlab_fallback(self, mock_manager):
        """Test open_pr with GitLab fallback."""
        mock_manager.create_branch.return_value = True
        mock_manager.commit_changes.return_value = True
        mock_manager.push_branch.return_value = True
        mock_manager.create_github_pr.return_value = (None, None, False, "Failed")
        mock_manager.create_gitlab_pr.return_value = (
            "https://gitlab.com/owner/repo/-/merge_requests/456",
            456,
            True,
            "MR created",
        )

        async def run_test():
            result = await server.call_tool(
                "open_pr",
                {
                    "branch": "feature-branch",
                    "title": "Test PR",
                    "description": "Test description",
                },
            )
            assert len(result) == 1
            mock_manager.create_gitlab_pr.assert_called_once()

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_invalid_path(self, mock_manager, tmp_path):
        """Test write_doc with invalid path."""
        mock_manager.workspace_root = tmp_path

        # Security validation will catch this before it reaches write_doc
        async def run_test():
            result = await server.call_tool(
                "write_doc", {"path": "../../etc/passwd", "content": "test"}
            )
            assert len(result) == 1
            assert "error" in result[0].text.lower()

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_security_error(self, mock_manager, tmp_path):
        """Test call_tool with ValidationError for invalid feature_id."""
        mock_manager.workspace_root = tmp_path

        async def run_test():
            # Test with invalid feature_id
            result = await server.call_tool(
                "suggest_doc_location", {"feature_id": "feature;rm -rf /"}
            )
            assert len(result) == 1
            assert "error" in result[0].text.lower()
            assert "validation" in result[0].text.lower()

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_missing_required_fields(self, mock_manager):
        """Test call_tool with missing required fields."""

        async def run_test():
            # Missing feature_id
            result = await server.call_tool("suggest_doc_location", {})
            assert len(result) == 1
            assert "error" in result[0].text.lower()

            # Missing path
            result = await server.call_tool("write_doc", {"content": "test"})
            assert len(result) == 1
            assert "error" in result[0].text.lower()

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_unknown_tool(self, mock_manager):
        """Test call_tool with unknown tool name."""

        async def run_test():
            result = await server.call_tool("unknown_tool", {})
            assert len(result) == 1
            assert "error" in result[0].text.lower()

        asyncio.run(run_test())
