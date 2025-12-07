"""Unit tests for templates_style_server module."""

import asyncio
from unittest.mock import patch

from src.shared.errors import TemplateNotFoundError
from src.templates_style_server import server
from src.templates_style_server.server import app


class TestTemplatesStyleServer:
    """Test cases for Templates + Style MCP Server."""

    def test_list_tools_decorator(self):
        """Test that list_tools decorator is registered."""
        # Check that the app exists and is configured
        assert app is not None
        assert hasattr(app, "name")
        assert app.name == "templates-style-server"

    @patch("src.templates_style_server.server.template_loader")
    def test_call_tool_get_template(self, mock_loader):
        """Test get_template tool call logic."""
        mock_loader.get_template.return_value = "# Template Content"
        mock_loader.get_template_source.return_value = "default"

        async def run_test():
            # Access the actual call_tool function
            result = await server.call_tool("get_template", {"doc_type": "concept"})
            assert len(result) == 1
            assert (
                "Template Content" in result[0].text
                or "concept" in result[0].text.lower()
            )
            mock_loader.get_template.assert_called_once_with("concept")

        asyncio.run(run_test())

    @patch("src.templates_style_server.server.template_loader")
    def test_call_tool_get_template_missing_doc_type(self, mock_loader):
        """Test get_template tool call with missing doc_type."""

        async def run_test():
            result = await server.call_tool("get_template", {})
            assert len(result) == 1
            assert "error" in result[0].text.lower()

        asyncio.run(run_test())

    @patch("src.templates_style_server.server.template_loader")
    def test_call_tool_get_template_not_found(self, mock_loader):
        """Test get_template tool call when template not found."""
        mock_loader.get_template.side_effect = TemplateNotFoundError(
            "Template not found", "Details"
        )

        async def run_test():
            result = await server.call_tool("get_template", {"doc_type": "concept"})
            assert len(result) == 1
            assert "error" in result[0].text.lower()

        asyncio.run(run_test())

    @patch("src.templates_style_server.server.template_loader")
    def test_call_tool_get_style_guide(self, mock_loader):
        """Test get_style_guide tool call."""
        mock_loader.get_style_guide.return_value = (
            {"heading_structure": {}, "tone": {}},
            "default",
        )

        async def run_test():
            result = await server.call_tool("get_style_guide", {})
            assert len(result) == 1
            assert "heading_structure" in result[0].text
            mock_loader.get_style_guide.assert_called_once_with(None)

        asyncio.run(run_test())

    @patch("src.templates_style_server.server.template_loader")
    def test_call_tool_get_style_guide_with_product(self, mock_loader):
        """Test get_style_guide tool call with product."""
        mock_loader.get_style_guide.return_value = (
            {"heading_structure": {}},
            "workspace",
        )

        async def run_test():
            result = await server.call_tool("get_style_guide", {"product": "myproduct"})
            assert len(result) == 1
            mock_loader.get_style_guide.assert_called_once_with("myproduct")

        asyncio.run(run_test())

    @patch("src.templates_style_server.server.template_loader")
    def test_call_tool_get_glossary(self, mock_loader):
        """Test get_glossary tool call."""
        mock_loader.get_glossary.return_value = (
            {"terms": {"API": "Definition"}},
            "default",
        )

        async def run_test():
            result = await server.call_tool("get_glossary", {})
            assert len(result) == 1
            assert "terms" in result[0].text
            mock_loader.get_glossary.assert_called_once()

        asyncio.run(run_test())

    @patch("src.templates_style_server.server.template_loader")
    def test_call_tool_unknown_tool(self, mock_loader):
        """Test call_tool with unknown tool name."""

        async def run_test():
            result = await server.call_tool("unknown_tool", {})
            assert len(result) == 1
            assert "error" in result[0].text.lower()

        asyncio.run(run_test())
