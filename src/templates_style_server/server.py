"""Templates + Style MCP Server implementation."""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.shared.config import TemplatesStyleConfig
from src.shared.errors import DocsCopilotError, TemplateNotFoundError
from src.shared.logging import setup_logging
from src.templates_style_server.models import Glossary, StyleGuide, Template
from src.templates_style_server.template_loader import TemplateLoader

# Initialize logger
logger = setup_logging()

# Initialize server
app = Server("templates-style-server")

# Initialize configuration
config = TemplatesStyleConfig.from_env()

# Initialize template loader
template_loader = TemplateLoader(config)


@app.list_tools()  # type: ignore[untyped-decorator]
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_template",
            description="Get documentation template for a specific document type",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_type": {
                        "type": "string",
                        "description": "Document type (concept, task, api_reference, release_notes, feature_overview, configuration_reference)",
                        "enum": [
                            "concept",
                            "task",
                            "api_reference",
                            "release_notes",
                            "feature_overview",
                            "configuration_reference",
                        ],
                    },
                },
                "required": ["doc_type"],
            },
        ),
        Tool(
            name="get_style_guide",
            description="Get style guide for documentation",
            inputSchema={
                "type": "object",
                "properties": {
                    "product": {
                        "type": "string",
                        "description": "Optional product name for product-specific style guide",
                    },
                },
            },
        ),
        Tool(
            name="get_glossary",
            description="Get glossary of terms",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()  # type: ignore[untyped-decorator]
async def call_tool(
    name: str, arguments: dict[str, Any] | None = None
) -> list[TextContent]:
    """Handle tool calls."""
    if arguments is None:
        arguments = {}
    try:
        if name == "get_template":
            doc_type = arguments.get("doc_type")

            if not doc_type:
                raise ValueError("doc_type is required")

            content = template_loader.get_template(doc_type)
            source = template_loader.get_template_source(doc_type)

            template = Template(doc_type=doc_type, content=content, source=source)

            return [
                TextContent(
                    type="text",
                    text=template.model_dump_json(indent=2),
                )
            ]

        elif name == "get_style_guide":
            product = arguments.get("product")

            data, source = template_loader.get_style_guide(product)

            style_guide = StyleGuide(
                product=product,
                heading_structure=data.get("heading_structure", {}),
                tone=data.get("tone", {}),
                formatting=data.get("formatting", {}),
                source=source,
            )

            return [
                TextContent(
                    type="text",
                    text=style_guide.model_dump_json(indent=2),
                )
            ]

        elif name == "get_glossary":
            data, source = template_loader.get_glossary()

            terms = data.get("terms", {})
            glossary = Glossary(terms=terms, source=source)

            return [
                TextContent(
                    type="text",
                    text=glossary.model_dump_json(indent=2),
                )
            ]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except TemplateNotFoundError as e:
        logger.warning(f"Template not found: {e.message}")
        return [
            TextContent(
                type="text",
                text=f'{{"error": "Template not found", "message": "{e.message}"}}',
            )
        ]
    except DocsCopilotError as e:
        logger.error(f"DocsCopilot error: {e.message}")
        return [
            TextContent(
                type="text",
                text=f'{{"error": "DocsCopilot error", "message": "{e.message}"}}',
            )
        ]
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return [
            TextContent(
                type="text",
                text=f'{{"error": "Unexpected error", "message": "{str(e)}"}}',
            )
        ]


async def main() -> None:
    """Main entry point."""
    logger.info("Starting Templates + Style MCP Server")
    logger.info(f"Workspace root: {config.workspace_root}")
    logger.info(f"Templates path: {config.templates_path}")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
