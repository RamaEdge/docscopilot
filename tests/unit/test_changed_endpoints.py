"""Unit tests for changed_endpoints module."""

from unittest.mock import patch

import pytest

from src.code_context_server.changed_endpoints import ChangedEndpointsExtractor
from src.shared.git_utils import GitUtils


@pytest.mark.unit
class TestChangedEndpointsExtractor:
    """Test cases for ChangedEndpointsExtractor class."""

    def test_init(self, tmp_path):
        """Test ChangedEndpointsExtractor initialization."""
        git_utils = GitUtils(tmp_path)
        extractor = ChangedEndpointsExtractor(git_utils, tmp_path)
        assert extractor.git_utils == git_utils
        assert extractor.workspace_root == tmp_path

    def test_get_changed_endpoints_from_diff(self, tmp_path):
        """Test extracting endpoints from diff string."""
        git_utils = GitUtils(tmp_path)
        extractor = ChangedEndpointsExtractor(git_utils, tmp_path)

        diff = """diff --git a/api.py b/api.py
+++ b/api.py
@@ -1,0 +1,5 @@
+@app.get("/users")
+def get_users():
+    return []
"""

        endpoints = extractor.get_changed_endpoints(diff)
        assert len(endpoints.endpoints) > 0

    def test_get_changed_endpoints_no_diff(self, tmp_path):
        """Test extracting endpoints without diff."""
        git_utils = GitUtils(tmp_path)
        extractor = ChangedEndpointsExtractor(git_utils, tmp_path)

        endpoints = extractor.get_changed_endpoints(None)
        assert len(endpoints.endpoints) == 0

    @patch.object(GitUtils, "get_diff")
    def test_get_changed_endpoints_from_git(self, mock_get_diff, tmp_path):
        """Test extracting endpoints from git diff."""
        mock_get_diff.return_value = """+++ b/api.py
+@app.get("/users")
+def get_users():
+    return []
"""

        git_utils = GitUtils(tmp_path)
        extractor = ChangedEndpointsExtractor(git_utils, tmp_path)
        (tmp_path / ".git").mkdir()

        endpoints = extractor.get_changed_endpoints(None, tmp_path, "main", "feature")
        assert len(endpoints.endpoints) > 0
