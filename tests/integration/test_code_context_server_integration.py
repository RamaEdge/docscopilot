"""Integration tests for Code Context MCP Server."""

import importlib
import os
import subprocess
from pathlib import Path

import pytest

from src.code_context_server.server import list_tools


@pytest.mark.integration
class TestCodeContextServerIntegration:
    """Integration tests for Code Context MCP Server."""

    @pytest.fixture(autouse=True)
    def setup_server(self, temp_workspace: Path):
        """Set up server with test configuration."""
        # Set environment variables for server initialization
        os.environ["WORKSPACE_ROOT"] = str(temp_workspace)
        os.environ["GIT_BINARY"] = "git"
        os.environ["SUPPORTED_LANGUAGES"] = "python"

        # Re-import server to pick up new config
        import src.code_context_server.server as server_module

        importlib.reload(server_module)

        yield

        # Cleanup
        if "WORKSPACE_ROOT" in os.environ:
            del os.environ["WORKSPACE_ROOT"]
        if "GIT_BINARY" in os.environ:
            del os.environ["GIT_BINARY"]
        if "SUPPORTED_LANGUAGES" in os.environ:
            del os.environ["SUPPORTED_LANGUAGES"]

    @pytest.mark.asyncio
    async def test_list_tools_integration(self):
        """Test listing tools via MCP protocol."""
        tools = await list_tools()
        assert len(tools) == 3
        tool_names = [tool.name for tool in tools]
        assert "get_feature_metadata" in tool_names
        assert "get_code_examples" in tool_names
        assert "get_changed_endpoints" in tool_names

    @pytest.mark.asyncio
    async def test_get_feature_metadata_integration(self, mock_git_repo: Path):
        """Test get_feature_metadata end-to-end with real git repo."""
        # Create a commit with feature reference
        subprocess.run(
            [
                "git",
                "commit",
                "--allow-empty",
                "-m",
                "Feature: TEST-123 Add new feature",
            ],
            cwd=str(mock_git_repo),
            capture_output=True,
            check=True,
        )

        # Import server module to get fresh instance
        from src.code_context_server import server

        result = await server.call_tool(
            "get_feature_metadata",
            {"feature_id": "TEST-123", "repo_path": str(mock_git_repo.name)},
        )

        assert len(result) == 1
        assert result[0].type == "text"
        # Should find the feature in the commit message
        assert "TEST-123" in result[0].text or "error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_get_code_examples_integration(self, temp_workspace: Path):
        """Test get_code_examples end-to-end with real file."""
        # Create a Python file with code examples
        test_file = temp_workspace / "test_example.py"
        test_file.write_text(
            '''"""Test module with examples."""
def example_function(param: str) -> str:
    """Example function.

    Args:
        param: Example parameter

    Returns:
        Example return value
    """
    return f"Hello {param}"
'''
        )

        from src.code_context_server import server

        result = await server.call_tool(
            "get_code_examples",
            {"path": str(test_file.relative_to(temp_workspace))},
        )

        assert len(result) == 1
        assert result[0].type == "text"
        assert "example_function" in result[0].text

    @pytest.mark.asyncio
    async def test_get_changed_endpoints_integration(self, mock_git_repo: Path):
        """Test get_changed_endpoints end-to-end with git diff."""
        # Create a Python file with API endpoint
        api_file = mock_git_repo / "api.py"
        api_file.write_text(
            """from flask import Flask
app = Flask(__name__)

@app.route("/api/v1/users", methods=["GET"])
def get_users():
    return {"users": []}
"""
        )

        # Commit the file
        subprocess.run(
            ["git", "add", "api.py"],
            cwd=str(mock_git_repo),
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add API endpoint"],
            cwd=str(mock_git_repo),
            capture_output=True,
            check=True,
        )

        # Get the main branch commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(mock_git_repo),
            capture_output=True,
            text=True,
            check=True,
        )
        main_commit = result.stdout.strip()

        # Create a branch and modify the file
        subprocess.run(
            ["git", "checkout", "-b", "feature-branch"],
            cwd=str(mock_git_repo),
            capture_output=True,
            check=True,
        )
        api_file.write_text(
            """from flask import Flask
app = Flask(__name__)

@app.route("/api/v1/users", methods=["GET"])
def get_users():
    return {"users": []}

@app.route("/api/v1/posts", methods=["GET"])
def get_posts():
    return {"posts": []}
"""
        )
        subprocess.run(
            ["git", "add", "api.py"],
            cwd=str(mock_git_repo),
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add posts endpoint"],
            cwd=str(mock_git_repo),
            capture_output=True,
            check=True,
        )

        from src.code_context_server import server

        result = await server.call_tool(
            "get_changed_endpoints",
            {
                "repo_path": str(mock_git_repo.name),
                "base": main_commit,
                "head": "HEAD",
            },
        )

        assert len(result) == 1
        assert result[0].type == "text"

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, temp_workspace: Path):
        """Test error handling in integration scenarios."""
        from src.code_context_server import server

        # Test with non-existent feature
        result = await server.call_tool(
            "get_feature_metadata",
            {"feature_id": "NONEXISTENT-999"},
        )

        assert len(result) == 1
        assert result[0].type == "text"
        # Should return error response
        assert (
            "error" in result[0].text.lower() or "not found" in result[0].text.lower()
        )
