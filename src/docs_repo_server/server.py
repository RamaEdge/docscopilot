"""Docs Repo MCP Server implementation."""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.docs_repo_server.models import DocLocation, PRResult, WriteResult
from src.docs_repo_server.repo_manager import RepoManager
from src.shared.config import DocsRepoConfig
from src.shared.errors import (
    DocsCopilotError,
    ErrorCode,
    InvalidPathError,
    ValidationError,
)
from src.shared.logging import setup_logging
from src.shared.validation import validate_branch_name, validate_doc_type

# Initialize logger
logger = setup_logging()

# Initialize server
app = Server("docs-repo-server")

# Initialize configuration
config = DocsRepoConfig.from_env()

# Initialize repository manager
repo_manager = RepoManager(config)


@app.list_tools()  # type: ignore[untyped-decorator]
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="suggest_doc_location",
            description="Suggest documentation location for a feature",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {
                        "type": "string",
                        "description": "Feature identifier",
                    },
                    "doc_type": {
                        "type": "string",
                        "description": "Optional document type (concept, task, api_reference, etc.)",
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
                "required": ["feature_id"],
            },
        ),
        Tool(
            name="write_doc",
            description="Write documentation file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path (relative to workspace_root or absolute)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Document content (markdown)",
                    },
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="open_pr",
            description="Create a pull request with documentation changes",
            inputSchema={
                "type": "object",
                "properties": {
                    "branch": {
                        "type": "string",
                        "description": "Branch name",
                    },
                    "title": {
                        "type": "string",
                        "description": "PR title",
                    },
                    "description": {
                        "type": "string",
                        "description": "PR description",
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of files to commit",
                    },
                },
                "required": ["branch", "title", "description"],
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
        if name == "suggest_doc_location":
            feature_id = arguments.get("feature_id")
            doc_type = arguments.get("doc_type")

            if not feature_id:
                raise ValidationError("feature_id is required")

            # Validate inputs
            from src.shared.validation import validate_feature_id

            validated_feature_id = validate_feature_id(feature_id)
            validated_doc_type = validate_doc_type(doc_type)

            path, final_doc_type = repo_manager.suggest_doc_location(
                validated_feature_id, validated_doc_type
            )

            location = DocLocation(
                path=path,
                doc_type=final_doc_type,
                reason=f"Suggested location for {feature_id}",
            )

            return [
                TextContent(
                    type="text",
                    text=location.model_dump_json(indent=2),
                )
            ]

        elif name == "write_doc":
            doc_path: str | None = arguments.get("path")
            doc_content: str | None = arguments.get("content")

            if not doc_path:
                raise ValueError("path is required")
            if not doc_content:
                raise ValueError("content is required")

            actual_path, success, message = repo_manager.write_doc(
                doc_path, doc_content
            )

            result = WriteResult(path=actual_path, success=success, message=message)

            return [
                TextContent(
                    type="text",
                    text=result.model_dump_json(indent=2),
                )
            ]

        elif name == "open_pr":
            branch = arguments.get("branch")
            title = arguments.get("title")
            description = arguments.get("description")
            files = arguments.get("files")

            if not branch:
                raise ValidationError("branch is required")
            if not title:
                raise ValidationError("title is required")
            if not description:
                raise ValidationError("description is required")

            # Validate branch name
            validated_branch = validate_branch_name(branch)

            if not isinstance(title, str) or len(title) > 200:
                raise ValidationError(
                    "title must be a string with 200 characters or less"
                )
            if not isinstance(description, str) or len(description) > 10000:
                raise ValidationError(
                    "description must be a string with 10000 characters or less"
                )

            # Create branch
            if not repo_manager.create_branch(validated_branch):
                return [
                    TextContent(
                        type="text",
                        text='{"error": "Failed to create branch", "message": "Could not create git branch"}',
                    )
                ]

            # Commit changes
            commit_message = f"{title}\n\n{description}"
            if not repo_manager.commit_changes(commit_message, files):
                return [
                    TextContent(
                        type="text",
                        text='{"error": "Failed to commit changes", "message": "Could not commit changes"}',
                    )
                ]

            # Push branch
            if not repo_manager.push_branch(validated_branch):
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": "Failed to push branch",
                                "message": "Could not push branch to remote",
                                "error_code": ErrorCode.GIT_COMMAND_FAILED.value,
                            },
                            indent=2,
                        ),
                    )
                ]

            # Create PR (try GitHub first, then GitLab)
            pr_url, pr_number, success, message = repo_manager.create_github_pr(
                validated_branch, title, description
            )

            if not success:
                # Try GitLab
                pr_url, pr_number, success, message = repo_manager.create_gitlab_pr(
                    validated_branch, title, description
                )

            pr_result = PRResult(
                pr_url=pr_url or "",
                branch=validated_branch,
                pr_number=pr_number,
                success=success,
                message=message,
            )

            return [
                TextContent(
                    type="text",
                    text=pr_result.model_dump_json(indent=2),
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
    except InvalidPathError as e:
        logger.warning(f"Invalid path: {e.message}")
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
    logger.info("Starting Docs Repo MCP Server")
    logger.info(f"Workspace root: {config.workspace_root}")
    logger.info(f"Repo mode: {repo_manager.repo_mode}")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
