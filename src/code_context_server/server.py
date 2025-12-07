"""Code Context MCP Server implementation."""

import asyncio
import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.code_context_server.changed_endpoints import ChangedEndpointsExtractor
from src.code_context_server.code_examples import CodeExamplesExtractor
from src.code_context_server.feature_metadata import FeatureMetadataExtractor
from src.shared.config import CodeContextConfig
from src.shared.errors import (
    DocsCopilotError,
    ErrorCode,
    FeatureNotFoundError,
    FileNotFoundError,
    GitCommandError,
    GitTimeoutError,
    RepositoryNotFoundError,
    ValidationError,
)
from src.shared.git_utils import GitUtils
from src.shared.logging import setup_logging
from src.shared.validation import validate_feature_id

# Initialize logger
logger = setup_logging()

# Initialize server
app = Server("code-context-server")

# Initialize configuration
config = CodeContextConfig.from_env()

# Initialize utilities
git_utils = GitUtils(config.workspace_root, config.git_binary)
feature_extractor = FeatureMetadataExtractor(git_utils, config.workspace_root)
code_examples_extractor = CodeExamplesExtractor(config.supported_languages)
endpoints_extractor = ChangedEndpointsExtractor(git_utils, config.workspace_root)


@app.list_tools()  # type: ignore[untyped-decorator]
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_feature_metadata",
            description="Get metadata about a feature from git repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {
                        "type": "string",
                        "description": "Feature identifier to search for",
                    },
                    "repo_path": {
                        "type": "string",
                        "description": "Optional path to specific repository (relative to workspace_root)",
                    },
                },
                "required": ["feature_id"],
            },
        ),
        Tool(
            name="get_code_examples",
            description="Extract code examples from a source file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to source file (relative to workspace_root or absolute)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="get_changed_endpoints",
            description="Extract changed API endpoints from a git diff",
            inputSchema={
                "type": "object",
                "properties": {
                    "diff": {
                        "type": "string",
                        "description": "Git diff string (optional if base/head provided)",
                    },
                    "repo_path": {
                        "type": "string",
                        "description": "Path to repository (required if diff not provided)",
                    },
                    "base": {
                        "type": "string",
                        "description": "Base commit/branch (required if diff not provided)",
                    },
                    "head": {
                        "type": "string",
                        "description": "Head commit/branch (required if diff not provided)",
                    },
                },
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
        if name == "get_feature_metadata":
            feature_id = arguments.get("feature_id")
            repo_path = arguments.get("repo_path")

            if not feature_id:
                raise ValidationError("feature_id is required")

            # Validate feature ID
            validated_feature_id = validate_feature_id(feature_id)

            repo_path_obj = Path(repo_path) if repo_path else None
            metadata = feature_extractor.get_feature_metadata(
                validated_feature_id, repo_path_obj
            )

            return [
                TextContent(
                    type="text",
                    text=metadata.model_dump_json(indent=2),
                )
            ]

        elif name == "get_code_examples":
            path = arguments.get("path")

            if not path:
                raise ValidationError("path is required")

            if not isinstance(path, str):
                raise ValidationError(
                    f"path must be a string, got {type(path).__name__}"
                )

            examples = code_examples_extractor.get_code_examples(
                path, config.workspace_root
            )

            return [
                TextContent(
                    type="text",
                    text=examples.model_dump_json(indent=2),
                )
            ]

        elif name == "get_changed_endpoints":
            diff: str | None = arguments.get("diff")
            repo_path = arguments.get("repo_path")
            base = arguments.get("base")
            head = arguments.get("head")

            endpoints = endpoints_extractor.get_changed_endpoints(
                diff,
                Path(repo_path) if repo_path else None,
                base if base else None,
                head if head else None,
            )

            return [
                TextContent(
                    type="text",
                    text=endpoints.model_dump_json(indent=2),
                )
            ]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        return [
            TextContent(
                type="text",
                text=json.dumps(e.to_dict(), indent=2),
            )
        ]
    except FeatureNotFoundError as e:
        logger.warning(f"Feature not found: {e.message}")
        return [
            TextContent(
                type="text",
                text=json.dumps(e.to_dict(), indent=2),
            )
        ]
    except FileNotFoundError as e:
        logger.warning(f"File not found: {e.message}")
        return [
            TextContent(
                type="text",
                text=json.dumps(e.to_dict(), indent=2),
            )
        ]
    except GitTimeoutError as e:
        logger.error(f"Git timeout: {e.message}")
        return [
            TextContent(
                type="text",
                text=json.dumps(e.to_dict(), indent=2),
            )
        ]
    except (GitCommandError, RepositoryNotFoundError) as e:
        logger.error(f"Git error: {e.message}")
        return [
            TextContent(
                type="text",
                text=json.dumps(e.to_dict(), indent=2),
            )
        ]
    except DocsCopilotError as e:
        logger.error(f"DocsCopilot error: {e.message}")
        return [
            TextContent(
                type="text",
                text=json.dumps(e.to_dict(), indent=2),
            )
        ]
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "UnexpectedError",
                        "message": str(e),
                        "error_code": ErrorCode.UNKNOWN_ERROR.value,
                    },
                    indent=2,
                ),
            )
        ]


async def main() -> None:
    """Main entry point."""
    logger.info("Starting Code Context MCP Server")
    logger.info(f"Workspace root: {config.workspace_root}")
    logger.info(f"Git binary: {config.git_binary}")
    logger.info(f"Supported languages: {config.supported_languages}")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
