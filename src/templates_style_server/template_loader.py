"""Template loader with layered lookup support."""

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

from src.shared.config import TemplatesStyleConfig
from src.shared.errors import TemplateNotFoundError
from src.shared.logging import setup_logging

logger = setup_logging()


class TemplateLoader:
    """Loader for templates, style guides, and glossaries with layered lookup."""

    def __init__(self, config: TemplatesStyleConfig):
        """Initialize template loader.

        Args:
            config: TemplatesStyleConfig instance
        """
        self.config = config
        self.workspace_root = Path(config.workspace_root)

        # Define lookup paths in priority order
        self.lookup_paths = self._build_lookup_paths()

        # Initialize Jinja2 environment for template loading
        self.jinja_env = self._create_jinja_env()

    def _build_lookup_paths(self) -> list[Path]:
        """Build list of lookup paths in priority order.

        Returns:
            List of paths in priority order (highest priority first)
        """
        paths = []

        # 1. Configured path (highest priority)
        if self.config.templates_path:
            configured_path = Path(self.config.templates_path)
            if configured_path.exists():
                paths.append(configured_path)
            else:
                logger.warning(
                    f"Configured templates path does not exist: {configured_path}"
                )

        # 2. Workspace overrides
        workspace_path = self.workspace_root / ".docscopilot"
        if workspace_path.exists():
            paths.append(workspace_path)

        # 3. Built-in defaults (lowest priority)
        defaults_path = Path(__file__).parent / "defaults"
        if defaults_path.exists():
            paths.append(defaults_path)

        return paths

    def _create_jinja_env(self) -> Environment:
        """Create Jinja2 environment for template loading.

        Returns:
            Jinja2 Environment
        """
        # Collect all template directories
        template_dirs = []
        for lookup_path in self.lookup_paths:
            templates_dir = lookup_path / "templates"
            if templates_dir.exists():
                template_dirs.append(str(templates_dir))

        if not template_dirs:
            # Fallback to defaults if no directories found
            defaults_dir = Path(__file__).parent / "defaults" / "templates"
            template_dirs.append(str(defaults_dir))

        return Environment(
            loader=FileSystemLoader(template_dirs),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def get_template(self, doc_type: str) -> str:
        """Get template for a document type.

        Args:
            doc_type: Document type (concept, task, api_reference, etc.)

        Returns:
            Template content as string

        Raises:
            TemplateNotFoundError: If template is not found
        """
        # Validate doc_type
        valid_types = [
            "concept",
            "task",
            "api_reference",
            "release_notes",
            "feature_overview",
            "configuration_reference",
        ]
        if doc_type not in valid_types:
            raise TemplateNotFoundError(
                f"Invalid doc_type: {doc_type}",
                f"Valid types are: {', '.join(valid_types)}",
            )

        # Try to load template from filesystem directly (more reliable)
        template_name = f"{doc_type}.md.j2"
        for lookup_path in self.lookup_paths:
            templates_dir = lookup_path / "templates"
            template_path = templates_dir / template_name
            if template_path.exists():
                return template_path.read_text(encoding="utf-8")

        # Try alternative naming
        template_name = f"{doc_type}.j2"
        for lookup_path in self.lookup_paths:
            templates_dir = lookup_path / "templates"
            template_path = templates_dir / template_name
            if template_path.exists():
                return template_path.read_text(encoding="utf-8")

        raise TemplateNotFoundError(
            f"Template not found for doc_type: {doc_type}",
            f"Searched in: {', '.join(str(p) for p in self.lookup_paths)}",
        )

    def get_template_source(self, doc_type: str) -> str:
        """Get source location of template (for response metadata).

        Args:
            doc_type: Document type

        Returns:
            Source identifier (configured, workspace, default)
        """
        template_name = f"{doc_type}.md.j2"
        for i, lookup_path in enumerate(self.lookup_paths):
            templates_dir = lookup_path / "templates"
            template_path = templates_dir / template_name
            if template_path.exists():
                if i == 0:
                    return "configured"
                elif (
                    i == 1
                    and self.workspace_root / ".docscopilot" in lookup_path.parents
                ):
                    return "workspace"
                else:
                    return "default"

        return "default"

    def _load_yaml_file(self, filename: str, subdir: str) -> tuple[dict[str, Any], str]:
        """Load YAML file from lookup paths.

        Args:
            filename: Name of YAML file
            subdir: Subdirectory name (style_guides, glossaries)

        Returns:
            Tuple of (data dict, source identifier)
        """
        workspace_docscopilot = self.workspace_root / ".docscopilot"

        for lookup_path in self.lookup_paths:
            file_path = lookup_path / subdir / filename
            if file_path.exists():
                try:
                    with open(file_path, encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}

                    # Determine source based on lookup path
                    if (
                        self.config.templates_path
                        and Path(self.config.templates_path) == lookup_path
                    ):
                        source = "configured"
                    elif lookup_path == workspace_docscopilot:
                        source = "workspace"
                    else:
                        source = "default"

                    return data, source
                except Exception as e:
                    logger.warning(f"Error loading YAML file {file_path}: {e}")
                    continue

        # Return empty dict with default source if not found
        return {}, "default"

    def get_style_guide(self, product: str | None = None) -> tuple[dict[str, Any], str]:
        """Get style guide.

        Args:
            product: Optional product name (for product-specific style guides)

        Returns:
            Tuple of (style guide data, source identifier)
        """
        filename = f"{product}.yaml" if product else "default.yaml"
        data, source = self._load_yaml_file(filename, "style_guides")

        # If product-specific not found and product specified, fall back to default
        if product and not data:
            data, source = self._load_yaml_file("default.yaml", "style_guides")

        return data, source

    def get_glossary(self) -> tuple[dict[str, Any], str]:
        """Get glossary.

        Returns:
            Tuple of (glossary data, source identifier)
        """
        data, source = self._load_yaml_file("default.yaml", "glossaries")
        return data, source
