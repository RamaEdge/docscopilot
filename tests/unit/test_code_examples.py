"""Unit tests for code_examples module."""

import pytest

from src.code_context_server.code_examples import CodeExamplesExtractor
from src.shared.errors import FileNotFoundError


@pytest.mark.unit
class TestCodeExamplesExtractor:
    """Test cases for CodeExamplesExtractor class."""

    def test_init(self):
        """Test CodeExamplesExtractor initialization."""
        extractor = CodeExamplesExtractor(["python"])
        assert extractor.parser is not None

    def test_get_code_examples_file_not_found(self, tmp_path):
        """Test getting examples from non-existent file."""
        extractor = CodeExamplesExtractor()
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with pytest.raises(FileNotFoundError):
            extractor.get_code_examples("nonexistent.py", workspace)

    def test_get_code_examples_relative_path(self, tmp_path):
        """Test getting examples with relative path."""
        extractor = CodeExamplesExtractor(["python"])
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        test_file = workspace / "test.py"
        test_file.write_text(
            '''def hello():
    """Say hello."""
    return "Hello"
'''
        )

        examples = extractor.get_code_examples("test.py", workspace)
        assert examples.path == "test.py"
        assert len(examples.examples) > 0

    def test_get_code_examples_absolute_path(self, tmp_path):
        """Test getting examples with absolute path."""
        extractor = CodeExamplesExtractor(["python"])
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        test_file = workspace / "test.py"
        test_file.write_text('def hello(): return "Hello"')

        examples = extractor.get_code_examples(str(test_file), workspace)
        assert examples.path == "test.py"
        assert len(examples.examples) > 0

    def test_get_code_examples_path_outside_workspace(self, tmp_path):
        """Test getting examples with path outside workspace."""
        extractor = CodeExamplesExtractor()
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        outside_file = tmp_path / "outside.py"
        outside_file.write_text("content")

        with pytest.raises(FileNotFoundError):
            extractor.get_code_examples(str(outside_file), workspace)
