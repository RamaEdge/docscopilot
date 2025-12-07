"""Unit tests for docs_repo_server module."""

import asyncio
from unittest.mock import patch

import pytest

from src.docs_repo_server import server
from src.shared.errors import InvalidPathError


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
                "feature-123", None
            )

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_write_doc(self, mock_manager):
        """Test write_doc tool call."""
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
            mock_manager.write_doc.assert_called_once_with("docs/test.md", "# Test")

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_open_pr_success(self, mock_manager):
        """Test open_pr tool call success."""
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

        asyncio.run(run_test())

    @patch("src.docs_repo_server.server.repo_manager")
    def test_call_tool_open_pr_branch_failure(self, mock_manager):
        """Test open_pr with branch creation failure."""
        mock_manager.create_branch.return_value = False

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
    def test_call_tool_invalid_path(self, mock_manager):
        """Test write_doc with invalid path."""
        mock_manager.write_doc.side_effect = InvalidPathError("Invalid path", "Details")

        async def run_test():
            result = await server.call_tool(
                "write_doc", {"path": "../../etc/passwd", "content": "test"}
            )
            assert len(result) == 1
            assert "error" in result[0].text.lower()

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
