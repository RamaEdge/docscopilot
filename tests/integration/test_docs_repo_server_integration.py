"""Integration tests for Docs Repo MCP Server."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.docs_repo_server.server import call_tool, list_tools
from src.shared.config import DocsRepoConfig


@pytest.mark.integration
class TestDocsRepoServerIntegration:
    """Integration tests for Docs Repo MCP Server."""

    @pytest.fixture
    def server_config(
        self, temp_workspace: Path, mock_git_repo: Path
    ) -> DocsRepoConfig:
        """Create server configuration for testing."""
        return DocsRepoConfig(
            workspace_root=temp_workspace,
            github_token="test_token",
            gitlab_token="test_token",
        )

    @pytest.mark.asyncio
    async def test_list_tools_integration(self):
        """Test listing tools via MCP protocol."""
        tools = await list_tools()
        assert len(tools) == 3
        tool_names = [tool.name for tool in tools]
        assert "suggest_doc_location" in tool_names
        assert "write_doc" in tool_names
        assert "open_pr" in tool_names

    @pytest.mark.asyncio
    async def test_suggest_doc_location_integration(
        self, server_config: DocsRepoConfig
    ):
        """Test suggest_doc_location end-to-end."""
        with patch("src.docs_repo_server.server.config", server_config):
            with patch("src.docs_repo_server.server.repo_manager") as mock_manager:
                mock_manager.suggest_doc_location.return_value = (
                    "docs/concepts/test_feature.md",
                    "concept",
                )

                result = await call_tool(
                    "suggest_doc_location",
                    {"feature_id": "test_feature", "doc_type": "concept"},
                )

                assert len(result) == 1
                assert result[0].type == "text"
                assert "concepts" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_write_doc_integration(
        self, temp_workspace: Path, server_config: DocsRepoConfig
    ):
        """Test write_doc end-to-end with real file system."""
        # Use real repo_manager with test config
        from src.docs_repo_server.repo_manager import RepoManager
        from src.docs_repo_server.server import call_tool

        real_manager = RepoManager(server_config)

        with patch("src.docs_repo_server.server.config", server_config):
            with patch("src.docs_repo_server.server.repo_manager", real_manager):
                result = await call_tool(
                    "write_doc",
                    {
                        "path": "docs/test.md",
                        "content": "# Test Document\n\nThis is a test.",
                    },
                )

                assert len(result) == 1
                assert result[0].type == "text"
                assert "success" in result[0].text.lower()

                # Verify file was created
                test_file = temp_workspace / "docs" / "test.md"
                assert test_file.exists()
                assert "# Test Document" in test_file.read_text()

    @pytest.mark.asyncio
    async def test_open_pr_integration_github(
        self,
        mock_git_repo: Path,
        server_config: DocsRepoConfig,
        mock_github_api: MagicMock,
    ):
        """Test open_pr end-to-end with mocked GitHub API."""
        with patch("src.docs_repo_server.server.config", server_config):
            with patch("src.docs_repo_server.server.repo_manager") as mock_manager:
                # Mock git operations
                mock_manager.create_branch.return_value = True
                mock_manager.commit_changes.return_value = True
                mock_manager.push_branch.return_value = True
                mock_manager.create_github_pr.return_value = (
                    "https://github.com/owner/repo/pull/123",
                    123,
                    True,
                    "PR #123 created successfully",
                )

                result = await call_tool(
                    "open_pr",
                    {
                        "branch": "feature-branch",
                        "title": "Test PR",
                        "description": "Test description",
                        "files": ["docs/test.md"],
                    },
                )

                assert len(result) == 1
                assert result[0].type == "text"
                assert "123" in result[0].text or "success" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_open_pr_integration_gitlab(
        self,
        mock_git_repo: Path,
        server_config: DocsRepoConfig,
        mock_gitlab_api: MagicMock,
    ):
        """Test open_pr end-to-end with mocked GitLab API."""
        with patch("src.docs_repo_server.server.config", server_config):
            with patch("src.docs_repo_server.server.repo_manager") as mock_manager:
                # Mock GitHub failure, GitLab success
                mock_manager.create_branch.return_value = True
                mock_manager.commit_changes.return_value = True
                mock_manager.push_branch.return_value = True
                mock_manager.create_github_pr.return_value = (
                    None,
                    None,
                    False,
                    "GitHub token not configured",
                )
                mock_manager.create_gitlab_pr.return_value = (
                    "https://gitlab.com/owner/repo/-/merge_requests/456",
                    456,
                    True,
                    "MR !456 created successfully",
                )

                result = await call_tool(
                    "open_pr",
                    {
                        "branch": "feature-branch",
                        "title": "Test MR",
                        "description": "Test description",
                    },
                )

                assert len(result) == 1
                assert result[0].type == "text"
                assert "456" in result[0].text or "success" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_open_pr_branch_creation_failure(self, server_config: DocsRepoConfig):
        """Test open_pr when branch creation fails."""
        with patch("src.docs_repo_server.server.config", server_config):
            with patch("src.docs_repo_server.server.repo_manager") as mock_manager:
                mock_manager.create_branch.return_value = False

                result = await call_tool(
                    "open_pr",
                    {
                        "branch": "feature-branch",
                        "title": "Test PR",
                        "description": "Test description",
                    },
                )

                assert len(result) == 1
                assert result[0].type == "text"
                assert (
                    "error" in result[0].text.lower()
                    or "failed" in result[0].text.lower()
                )

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, server_config: DocsRepoConfig):
        """Test error handling for invalid paths."""
        with patch("src.docs_repo_server.server.config", server_config):
            from src.shared.errors import InvalidPathError

            with patch(
                "src.docs_repo_server.server.repo_manager.write_doc"
            ) as mock_write:
                mock_write.side_effect = InvalidPathError(
                    "Invalid path: ../../../etc/passwd",
                    "Path contains '..' which is not allowed",
                )

                result = await call_tool(
                    "write_doc",
                    {
                        "path": "../../../etc/passwd",
                        "content": "malicious content",
                    },
                )

                assert len(result) == 1
                assert result[0].type == "text"
                assert (
                    "error" in result[0].text.lower()
                    or "invalid" in result[0].text.lower()
                )
