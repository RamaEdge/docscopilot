"""Changed API endpoints extraction from git diffs."""

import re
from pathlib import Path

from src.code_context_server.models import ChangedEndpoints, EndpointInfo
from src.shared.errors import GitCommandError
from src.shared.git_utils import GitUtils


class ChangedEndpointsExtractor:
    """Extracts changed API endpoints from git diffs."""

    def __init__(self, git_utils: GitUtils, workspace_root: Path):
        """Initialize changed endpoints extractor.

        Args:
            git_utils: GitUtils instance
            workspace_root: Root directory containing repositories
        """
        self.git_utils = git_utils
        self.workspace_root = Path(workspace_root)

    def get_changed_endpoints(
        self,
        diff: str | None,
        repo_path: Path | None = None,
        base: str | None = None,
        head: str | None = None,
    ) -> ChangedEndpoints:
        """Get changed API endpoints from a diff.

        Args:
            diff: Git diff string or None to compute diff from base/head
            repo_path: Optional path to repository (required if diff is None)
            base: Base commit/branch (required if diff is None)
            head: Head commit/branch (required if diff is None)

        Returns:
            ChangedEndpoints object
        """
        if diff is None:
            if repo_path is None or base is None or head is None:
                return ChangedEndpoints(endpoints=[])
            try:
                diff = self.git_utils.get_diff(repo_path, base, head)
            except GitCommandError:
                return ChangedEndpoints(endpoints=[])

        endpoints = []
        current_file = None
        current_line = 0
        file_lines = diff.split("\n")

        for line in file_lines:
            # Detect file changes
            if line.startswith("diff --git") or line.startswith("+++ b/"):
                if line.startswith("+++ b/"):
                    current_file = line[6:].strip()
                continue

            # Detect new file
            if line.startswith("new file mode"):
                continue

            # Track line numbers
            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                if match:
                    current_line = int(match.group(1))
                continue

            # Parse added/modified lines for API endpoints
            if line.startswith("+") and not line.startswith("+++"):
                endpoint = self._parse_endpoint_line(
                    line[1:], current_file, current_line
                )
                if endpoint:
                    endpoints.append(endpoint)
                current_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                # Check for deleted endpoints
                endpoint = self._parse_endpoint_line(
                    line[1:], current_file, current_line, status="deleted"
                )
                if endpoint:
                    endpoints.append(endpoint)
            elif not line.startswith("-"):
                current_line += 1

        return ChangedEndpoints(endpoints=endpoints)

    def _parse_endpoint_line(
        self, line: str, file_path: str | None, line_num: int, status: str = "new"
    ) -> EndpointInfo | None:
        """Parse a line for API endpoint definitions.

        Args:
            line: Source code line
            file_path: File path
            line_num: Line number
            status: Status (new, modified, deleted)

        Returns:
            EndpointInfo or None
        """
        if not file_path or not file_path.endswith(".py"):
            return None

        # FastAPI/Flask route decorators
        route_patterns = [
            (
                r'@app\.(get|post|put|delete|patch|head|options)\s*\(["\']([^"\']+)["\']',
                "app",
            ),
            (
                r'@router\.(get|post|put|delete|patch|head|options)\s*\(["\']([^"\']+)["\']',
                "router",
            ),
            (
                r'@.*\.route\s*\(["\']([^"\']+)["\']\s*,\s*methods\s*=\s*\[["\'](\w+)["\']',
                None,
            ),
        ]

        for pattern, decorator_type in route_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                if decorator_type:
                    method = match.group(1).upper()
                    path = match.group(2)
                else:
                    path = match.group(1)
                    method = match.group(2).upper()

                # Try to find function name on next lines
                function_name = self._extract_function_name(line)

                return EndpointInfo(
                    method=method,
                    path=path,
                    function=function_name or "unknown",
                    file=file_path,
                    signature=None,
                    status=status,
                    line_numbers=(line_num, line_num),
                )

        return None

    def _extract_function_name(self, line: str) -> str | None:
        """Extract function name from a line (for decorator patterns).

        Args:
            line: Source code line

        Returns:
            Function name or None
        """
        # Look for function definition
        func_match = re.search(r"def\s+(\w+)\s*\(", line)
        if func_match:
            return func_match.group(1)
        return None
