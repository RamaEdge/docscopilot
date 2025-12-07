"""Unit tests for code_parser module."""

import pytest

from src.shared.code_parser import CodeParser
from src.shared.errors import FileNotFoundError


@pytest.mark.unit
class TestCodeParser:
    """Test cases for CodeParser class."""

    def test_init(self):
        """Test CodeParser initialization."""
        parser = CodeParser(["python"])
        assert parser.supported_languages == ["python"]

    def test_parse_file_not_found(self, tmp_path):
        """Test parsing non-existent file."""
        parser = CodeParser()
        non_existent = tmp_path / "nonexistent.py"

        with pytest.raises(FileNotFoundError):
            parser.parse_file(non_existent)

    def test_parse_python_file_with_function(self, tmp_path):
        """Test parsing Python file with function."""
        parser = CodeParser(["python"])
        test_file = tmp_path / "test.py"
        test_file.write_text(
            '''"""Module docstring."""

def hello_world(name: str) -> str:
    """Say hello to the world."""
    return f"Hello, {name}!"
'''
        )

        examples = parser.parse_file(test_file)
        assert len(examples) > 0
        assert any(
            ex.type == "function" and ex.name == "hello_world" for ex in examples
        )

    def test_parse_python_file_with_class(self, tmp_path):
        """Test parsing Python file with class."""
        parser = CodeParser(["python"])
        test_file = tmp_path / "test.py"
        test_file.write_text(
            '''"""Module docstring."""

class MyClass:
    """A test class."""

    def method(self):
        """A method."""
        pass
'''
        )

        examples = parser.parse_file(test_file)
        assert len(examples) > 0
        assert any(ex.type == "class" and ex.name == "MyClass" for ex in examples)

    def test_parse_generic_file(self, tmp_path):
        """Test parsing generic (non-Python) file."""
        parser = CodeParser(["python"])
        test_file = tmp_path / "test.txt"
        test_file.write_text("Some content\nMore content")

        examples = parser.parse_file(test_file)
        assert len(examples) == 1
        assert examples[0].type == "file"
        assert examples[0].name == "test.txt"

    def test_parse_invalid_python(self, tmp_path):
        """Test parsing invalid Python syntax."""
        parser = CodeParser(["python"])
        test_file = tmp_path / "test.py"
        test_file.write_text("def invalid syntax {")

        # Should not raise, but return file as single example
        examples = parser.parse_file(test_file)
        assert len(examples) == 1
        assert examples[0].type == "file"
