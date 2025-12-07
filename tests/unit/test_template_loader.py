"""Unit tests for template_loader module."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.shared.config import TemplatesStyleConfig
from src.shared.errors import TemplateNotFoundError
from src.templates_style_server.template_loader import TemplateLoader


class TestTemplateLoader:
    """Test cases for TemplateLoader class."""

    def test_init(self, tmp_path):
        """Test TemplateLoader initialization."""
        config = TemplatesStyleConfig(workspace_root=tmp_path)
        loader = TemplateLoader(config)
        assert loader.config == config
        assert loader.workspace_root == tmp_path

    def test_build_lookup_paths_defaults_only(self, tmp_path):
        """Test lookup paths with only defaults."""
        config = TemplatesStyleConfig(workspace_root=tmp_path)
        loader = TemplateLoader(config)
        paths = loader._build_lookup_paths()

        # Should have at least defaults path
        assert len(paths) >= 1
        assert any("defaults" in str(p) for p in paths)

    def test_build_lookup_paths_with_workspace(self, tmp_path):
        """Test lookup paths with workspace override."""
        workspace_path = tmp_path / ".docscopilot"
        workspace_path.mkdir()

        config = TemplatesStyleConfig(workspace_root=tmp_path)
        loader = TemplateLoader(config)
        paths = loader._build_lookup_paths()

        # Should have workspace and defaults
        assert len(paths) >= 2
        assert workspace_path in paths

    def test_build_lookup_paths_with_configured(self, tmp_path):
        """Test lookup paths with configured path."""
        configured_path = tmp_path / "custom_templates"
        configured_path.mkdir()

        config = TemplatesStyleConfig(
            workspace_root=tmp_path, templates_path=configured_path
        )
        loader = TemplateLoader(config)
        paths = loader._build_lookup_paths()

        # Should have configured path first
        assert paths[0] == configured_path

    def test_get_template_success(self, tmp_path):
        """Test successful template retrieval."""
        config = TemplatesStyleConfig(workspace_root=tmp_path)
        loader = TemplateLoader(config)

        # Should load from defaults
        template = loader.get_template("concept")
        assert isinstance(template, str)
        assert len(template) > 0

    def test_get_template_invalid_type(self, tmp_path):
        """Test template retrieval with invalid doc_type."""
        config = TemplatesStyleConfig(workspace_root=tmp_path)
        loader = TemplateLoader(config)

        with pytest.raises(TemplateNotFoundError):
            loader.get_template("invalid_type")

    def test_get_template_workspace_override(self, tmp_path):
        """Test template retrieval with workspace override."""
        workspace_path = tmp_path / ".docscopilot" / "templates"
        workspace_path.mkdir(parents=True)

        # Create custom template
        custom_template = workspace_path / "concept.md.j2"
        custom_template.write_text("# Custom Concept Template\n{{ title }}")

        config = TemplatesStyleConfig(workspace_root=tmp_path)
        loader = TemplateLoader(config)

        template = loader.get_template("concept")
        assert "Custom Concept Template" in template

    def test_get_template_source(self, tmp_path):
        """Test getting template source."""
        config = TemplatesStyleConfig(workspace_root=tmp_path)
        loader = TemplateLoader(config)

        source = loader.get_template_source("concept")
        assert source in ["configured", "workspace", "default"]

    def test_get_style_guide_default(self, tmp_path):
        """Test getting default style guide."""
        config = TemplatesStyleConfig(workspace_root=tmp_path)
        loader = TemplateLoader(config)

        data, source = loader.get_style_guide()
        assert isinstance(data, dict)
        assert source == "default"
        assert "heading_structure" in data or "tone" in data or "formatting" in data

    def test_get_style_guide_workspace_override(self, tmp_path):
        """Test getting style guide with workspace override."""
        workspace_path = tmp_path / ".docscopilot" / "style_guides"
        workspace_path.mkdir(parents=True)

        custom_style = {
            "heading_structure": {"levels": ["h1", "h2"]},
            "tone": {"style": "casual"},
        }
        style_file = workspace_path / "default.yaml"
        with open(style_file, "w") as f:
            yaml.dump(custom_style, f)

        config = TemplatesStyleConfig(workspace_root=tmp_path)
        loader = TemplateLoader(config)

        data, source = loader.get_style_guide()
        assert source == "workspace"
        assert data.get("tone", {}).get("style") == "casual"

    def test_get_style_guide_product_specific(self, tmp_path):
        """Test getting product-specific style guide."""
        workspace_path = tmp_path / ".docscopilot" / "style_guides"
        workspace_path.mkdir(parents=True)

        product_style = {"tone": {"style": "technical"}}
        product_file = workspace_path / "myproduct.yaml"
        with open(product_file, "w") as f:
            yaml.dump(product_style, f)

        config = TemplatesStyleConfig(workspace_root=tmp_path)
        loader = TemplateLoader(config)

        data, source = loader.get_style_guide("myproduct")
        assert source == "workspace"
        assert data.get("tone", {}).get("style") == "technical"

    def test_get_glossary_default(self, tmp_path):
        """Test getting default glossary."""
        config = TemplatesStyleConfig(workspace_root=tmp_path)
        loader = TemplateLoader(config)

        data, source = loader.get_glossary()
        assert isinstance(data, dict)
        assert source == "default"
        assert "terms" in data

    def test_get_glossary_workspace_override(self, tmp_path):
        """Test getting glossary with workspace override."""
        workspace_path = tmp_path / ".docscopilot" / "glossaries"
        workspace_path.mkdir(parents=True)

        custom_glossary = {"terms": {"CustomTerm": "Custom definition"}}
        glossary_file = workspace_path / "default.yaml"
        with open(glossary_file, "w") as f:
            yaml.dump(custom_glossary, f)

        config = TemplatesStyleConfig(workspace_root=tmp_path)
        loader = TemplateLoader(config)

        data, source = loader.get_glossary()
        assert source == "workspace"
        assert "CustomTerm" in data.get("terms", {})

