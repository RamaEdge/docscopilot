"""Code examples extraction from source files."""

from pathlib import Path

from src.code_context_server.models import CodeExample, CodeExamples
from src.shared.code_parser import CodeParser as SharedCodeParser
from src.shared.errors import FileNotFoundError


class CodeExamplesExtractor:
    """Extracts code examples from source files."""

    def __init__(self, supported_languages: list[str] | None = None):
        """Initialize code examples extractor.

        Args:
            supported_languages: List of supported programming languages
        """
        self.parser = SharedCodeParser(supported_languages)

    def get_code_examples(self, path: str, workspace_root: Path) -> CodeExamples:
        """Get code examples from a file.

        Args:
            path: Path to source file (relative to workspace_root or absolute)
            workspace_root: Root directory for resolving relative paths

        Returns:
            CodeExamples object

        Raises:
            FileNotFoundError: If file does not exist
        """
        workspace_root = Path(workspace_root)
        file_path = Path(path)

        # Resolve path
        if not file_path.is_absolute():
            file_path = workspace_root / file_path
        else:
            # Ensure path is within workspace for security
            try:
                file_path.resolve().relative_to(workspace_root.resolve())
            except ValueError as e:
                raise FileNotFoundError(
                    f"Path outside workspace: {path}",
                    f"File must be within workspace: {workspace_root}",
                ) from e

        # Parse file
        try:
            parsed_examples = self.parser.parse_file(file_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"File not found: {path}",
                str(e.details) if hasattr(e, "details") else None,
            ) from e

        # Convert to response models
        examples = []
        for ex in parsed_examples:
            examples.append(
                CodeExample(
                    type=ex.type,
                    name=ex.name,
                    code=ex.code,
                    docstring=ex.docstring,
                    line_numbers=ex.line_numbers,
                )
            )

        return CodeExamples(
            path=str(file_path.relative_to(workspace_root)),
            examples=examples,
        )
