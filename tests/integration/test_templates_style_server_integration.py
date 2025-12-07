"""Integration tests for Templates + Style MCP Server."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.shared.config import TemplatesStyleConfig
from src.templates_style_server.server import call_tool, list_tools


@pytest.mark.integration
@pytest.mark.asyncio
class TestTemplatesStyleServerIntegration:
    """Integration tests for Templates + Style MCP Server."""

    @pytest.fixture
    def server_config(self, temp_workspace: Path) -> TemplatesStyleConfig:
        """Create server configuration for testing."""
        # Create templates directory structure
        templates_dir = temp_workspace / ".docscopilot" / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Create a test template
        (templates_dir / "concept.md.j2").write_text(
            """# {{ title }}

{{ description }}

## Overview

{{ content }}
"""
        )

        # Create style guide
        style_dir = temp_workspace / ".docscopilot" / "style_guides"
        style_dir.mkdir(parents=True, exist_ok=True)
        (style_dir / "default.yaml").write_text(
            """heading_structure:
  h1: "Main title"
  h2: "Section"
tone:
  voice: "professional"
formatting:
  code_blocks: true
"""
        )

        # Create glossary
        glossary_dir = temp_workspace / ".docscopilot" / "glossaries"
        glossary_dir.mkdir(parents=True, exist_ok=True)
        (glossary_dir / "default.yaml").write_text(
            """terms:
  API: "Application Programming Interface"
  MCP: "Model Context Protocol"
"""
        )

        return TemplatesStyleConfig(
            workspace_root=temp_workspace,
            templates_path=str(temp_workspace / ".docscopilot"),
        )

    @pytest.mark.asyncio
    async def test_list_tools_integration(self):
        """Test listing tools via MCP protocol."""
        tools = await list_tools()
        assert len(tools) == 3
        tool_names = [tool.name for tool in tools]
        assert "get_template" in tool_names
        assert "get_style_guide" in tool_names
        assert "get_glossary" in tool_names

    @pytest.mark.asyncio
    async def test_get_template_integration(self, server_config: TemplatesStyleConfig):
        """Test get_template end-to-end with real file system."""
        with patch("src.templates_style_server.server.config", server_config):
            with patch(
                "src.templates_style_server.server.template_loader"
            ) as mock_loader:
                # Mock template loader to return our test template
                mock_loader.get_template.return_value = """# Test Title

Test description

## Overview

Test content
"""
                mock_loader.get_template_source.return_value = str(
                    server_config.templates_path / "templates" / "concept.md.j2"
                )

                result = await call_tool("get_template", {"doc_type": "concept"})

                assert len(result) == 1
                assert result[0].type == "text"
                assert "concept" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_get_style_guide_integration(
        self, server_config: TemplatesStyleConfig
    ):
        """Test get_style_guide end-to-end with real file system."""
        with patch("src.templates_style_server.server.config", server_config):
            with patch(
                "src.templates_style_server.server.template_loader"
            ) as mock_loader:
                mock_loader.get_style_guide.return_value = (
                    {
                        "heading_structure": {"h1": "Main title"},
                        "tone": {"voice": "professional"},
                        "formatting": {"code_blocks": True},
                    },
                    str(server_config.templates_path / "style_guides" / "default.yaml"),
                )

                result = await call_tool("get_style_guide", {})

                assert len(result) == 1
                assert result[0].type == "text"
                assert "professional" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_get_glossary_integration(self, server_config: TemplatesStyleConfig):
        """Test get_glossary end-to-end with real file system."""
        with patch("src.templates_style_server.server.config", server_config):
            with patch(
                "src.templates_style_server.server.template_loader"
            ) as mock_loader:
                mock_loader.get_glossary.return_value = (
                    {
                        "terms": {
                            "API": "Application Programming Interface",
                            "MCP": "Model Context Protocol",
                        }
                    },
                    str(server_config.templates_path / "glossaries" / "default.yaml"),
                )

                result = await call_tool("get_glossary", {})

                assert len(result) == 1
                assert result[0].type == "text"
                assert "API" in result[0].text or "MCP" in result[0].text

    @pytest.mark.asyncio
    async def test_error_handling_integration(
        self, server_config: TemplatesStyleConfig
    ):
        """Test error handling for non-existent template."""
        with patch("src.templates_style_server.server.config", server_config):
            with patch(
                "src.templates_style_server.server.template_loader.get_template"
            ) as mock_get_template:
                from src.shared.errors import TemplateNotFoundError

                mock_get_template.side_effect = TemplateNotFoundError(
                    "Template not found: invalid_type",
                    "Template type 'invalid_type' does not exist",
                )

                result = await call_tool("get_template", {"doc_type": "invalid_type"})

                assert len(result) == 1
                assert result[0].type == "text"
                assert (
                    "error" in result[0].text.lower()
                    or "not found" in result[0].text.lower()
                )
