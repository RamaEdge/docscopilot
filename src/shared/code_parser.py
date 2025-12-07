"""Code parsing utilities for extracting code examples."""

import ast
from pathlib import Path

from src.shared.errors import FileNotFoundError


class CodeExample:
    """Represents a code example extracted from source code."""

    def __init__(
        self,
        type: str,
        name: str,
        code: str,
        docstring: str | None = None,
        line_numbers: tuple[int, int] = (0, 0),
    ):
        """Initialize code example.

        Args:
            type: Type of code element (function, class, etc.)
            name: Name of the code element
            code: Source code
            docstring: Docstring if available
            line_numbers: Start and end line numbers
        """
        self.type = type
        self.name = name
        self.code = code
        self.docstring = docstring
        self.line_numbers = line_numbers


class CodeParser:
    """Parser for extracting code examples from source files."""

    def __init__(self, supported_languages: list[str] | None = None):
        """Initialize code parser.

        Args:
            supported_languages: List of supported programming languages
        """
        self.supported_languages = supported_languages or ["python"]

    def parse_file(self, file_path: Path) -> list[CodeExample]:
        """Parse a file and extract code examples.

        Args:
            file_path: Path to source file

        Returns:
            List of code examples

        Raises:
            FileNotFoundError: If file does not exist
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}",
                "Ensure the file exists and is accessible",
            )

        suffix = file_path.suffix.lower()
        if suffix == ".py" and "python" in self.supported_languages:
            return self._parse_python(file_path)
        else:
            # For unsupported languages, return file content as single example
            return self._parse_generic(file_path)

    def _parse_python(self, file_path: Path) -> list[CodeExample]:
        """Parse Python file using AST.

        Args:
            file_path: Path to Python file

        Returns:
            List of code examples
        """
        examples = []
        content = file_path.read_text(encoding="utf-8")

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            # If parsing fails, return file as single example
            return [
                CodeExample(
                    type="file",
                    name=file_path.name,
                    code=content,
                    line_numbers=(1, len(content.split("\n"))),
                )
            ]

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                example = self._extract_function(node, content, file_path)
                if example:
                    examples.append(example)
            elif isinstance(node, ast.ClassDef):
                example = self._extract_class(node, content, file_path)
                if example:
                    examples.append(example)

        return examples

    def _extract_function(
        self, node: ast.FunctionDef, content: str, file_path: Path
    ) -> CodeExample | None:
        """Extract function definition as code example.

        Args:
            node: AST function node
            content: File content
            file_path: Path to file

        Returns:
            CodeExample or None
        """
        lines = content.split("\n")
        start_line = node.lineno - 1
        end_lineno = getattr(node, "end_lineno", None)
        end_line = (end_lineno - 1) if end_lineno is not None else start_line

        function_code = "\n".join(lines[start_line : end_line + 1])
        docstring = ast.get_docstring(node)

        return CodeExample(
            type="function",
            name=node.name,
            code=function_code,
            docstring=docstring,
            line_numbers=(node.lineno, end_line + 1),
        )

    def _extract_class(
        self, node: ast.ClassDef, content: str, file_path: Path
    ) -> CodeExample | None:
        """Extract class definition as code example.

        Args:
            node: AST class node
            content: File content
            file_path: Path to file

        Returns:
            CodeExample or None
        """
        lines = content.split("\n")
        start_line = node.lineno - 1
        end_lineno = getattr(node, "end_lineno", None)
        end_line = (end_lineno - 1) if end_lineno is not None else start_line

        class_code = "\n".join(lines[start_line : end_line + 1])
        docstring = ast.get_docstring(node)

        return CodeExample(
            type="class",
            name=node.name,
            code=class_code,
            docstring=docstring,
            line_numbers=(node.lineno, end_line + 1),
        )

    def _parse_generic(self, file_path: Path) -> list[CodeExample]:
        """Parse generic file (non-Python).

        Args:
            file_path: Path to file

        Returns:
            List with single code example containing file content
        """
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        return [
            CodeExample(
                type="file",
                name=file_path.name,
                code=content,
                line_numbers=(1, len(lines)),
            )
        ]
