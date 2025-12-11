"""Docs Repo MCP Server implementation."""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.docs_repo_server.models import DocLocation, PRResult, WriteResult
from src.docs_repo_server.repo_manager import RepoManager
from src.shared.config import DocsRepoConfig
from src.shared.errors import DocsCopilotError, InvalidPathError
from src.shared.logging import setup_logging
from src.shared.security import SecurityError, SecurityValidator

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
                        "description": "Optional branch name (auto-generated from title/feature_id if not provided)",
                    },
                    "title": {
                        "type": "string",
                        "description": "PR title",
                    },
                    "description": {
                        "type": "string",
                        "description": "PR description",
                    },
                    "feature_id": {
                        "type": "string",
                        "description": "Optional feature ID for better branch naming",
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of files to commit",
                    },
                },
                "required": ["title", "description"],
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
                raise ValueError("feature_id is required")

            # Validate feature_id for security
            feature_id = SecurityValidator.validate_feature_id(feature_id)

            # Validate doc_type if provided
            validated_doc_type = None
            if doc_type:
                validated_doc_type = SecurityValidator.validate_doc_type(doc_type)

            path, final_doc_type = repo_manager.suggest_doc_location(
                feature_id, validated_doc_type
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

            # Validate path for security
            validated_path = SecurityValidator.validate_path(
                doc_path, repo_manager.workspace_root
            )
            actual_path, success, message = repo_manager.write_doc(
                str(validated_path.relative_to(repo_manager.workspace_root)),
                doc_content,
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
            feature_id = arguments.get("feature_id")
            files = arguments.get("files")

            if not title:
                raise ValueError("title is required")
            if not description:
                raise ValueError("description is required")

            # Auto-generate branch if not provided
            if not branch:
                # Validate feature_id if provided
                if feature_id:
                    feature_id = SecurityValidator.validate_feature_id(feature_id)
                branch = repo_manager.generate_branch_name(
                    title=title,
                    feature_id=feature_id,
                )
                logger.info(f"Auto-generated branch name: {branch}")
            else:
                # Validate user-provided branch name for security
                branch = SecurityValidator.validate_branch_name(branch)

            # Validate file paths if provided
            validated_files = None
            if files:
                validated_files = []
                for file_path in files:
                    validated_path = SecurityValidator.validate_path(
                        file_path, repo_manager.workspace_root
                    )
                    validated_files.append(
                        str(validated_path.relative_to(repo_manager.workspace_root))
                    )

            # Create branch
            if not repo_manager.create_branch(branch):
                return [
                    TextContent(
                        type="text",
                        text='{"error": "Failed to create branch", "message": "Could not create git branch"}',
                    )
                ]

            # Commit changes
            commit_message = f"{title}\n\n{description}"
            if not repo_manager.commit_changes(commit_message, validated_files):
                return [
                    TextContent(
                        type="text",
                        text='{"error": "Failed to commit changes", "message": "Could not commit changes"}',
                    )
                ]

            # Push branch
            if not repo_manager.push_branch(branch):
                return [
                    TextContent(
                        type="text",
                        text='{"error": "Failed to push branch", "message": "Could not push branch to remote"}',
                    )
                ]

            # Create PR (try GitHub first, then GitLab)
            pr_url, pr_number, success, message = repo_manager.create_github_pr(
                branch, title, description
            )

            if not success:
                # Try GitLab
                pr_url, pr_number, success, message = repo_manager.create_gitlab_pr(
                    branch, title, description
                )

            pr_result = PRResult(
                pr_url=pr_url or "",
                branch=branch,
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

    except SecurityError as e:
        logger.warning(f"Security validation error: {e.message}")
        return [
            TextContent(
                type="text",
                text=f'{{"error": "Security validation error", "message": "{e.message}"}}',
            )
        ]
    except InvalidPathError as e:
        logger.warning(f"Invalid path: {e.message}")
        return [
            TextContent(
                type="text",
                text=f'{{"error": "Invalid path", "message": "{e.message}"}}',
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
