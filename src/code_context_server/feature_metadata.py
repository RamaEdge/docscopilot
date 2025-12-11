"""Feature metadata extraction from git repositories."""

import re
from pathlib import Path

from src.code_context_server.models import CommitInfo, FeatureMetadata
from src.shared.errors import FeatureNotFoundError, GitCommandError
from src.shared.git_utils import GitUtils
from src.shared.security import SecurityValidator


class FeatureMetadataExtractor:
    """Extracts feature metadata from git repositories."""

    def __init__(self, git_utils: GitUtils, workspace_root: Path):
        """Initialize feature metadata extractor.

        Args:
            git_utils: GitUtils instance
            workspace_root: Root directory containing repositories
        """
        self.git_utils = git_utils
        self.workspace_root = Path(workspace_root)

    def get_feature_metadata(
        self, feature_id: str, repo_path: Path | None = None
    ) -> FeatureMetadata:
        """Get metadata for a feature.

        Args:
            feature_id: Feature identifier to search for (must be validated)
            repo_path: Optional path to specific repository.
                      If None, searches workspace_root

        Returns:
            FeatureMetadata object

        Raises:
            FeatureNotFoundError: If feature is not found
        """
        # Feature ID should already be validated, but ensure it's safe for git commands
        feature_id = SecurityValidator.sanitize_git_pattern(feature_id)

        if repo_path is None:
            repo_path = self.workspace_root
        else:
            repo_path = Path(repo_path)

        # Search for commits mentioning the feature
        try:
            commit_hashes = self.git_utils.log_grep(repo_path, feature_id)
        except GitCommandError:
            commit_hashes = []

        if not commit_hashes:
            raise FeatureNotFoundError(
                f"Feature '{feature_id}' not found in repository",
                f"No commits found matching pattern: {feature_id}",
            )

        # Get commit information
        commits = []
        branches = set()
        tags = set()
        code_paths = set()
        descriptions = []
        related_issues = []

        for commit_hash in commit_hashes:
            try:
                commit_info = self.git_utils.get_commit_info(repo_path, commit_hash)
                commits.append(
                    CommitInfo(
                        hash=commit_info["hash"],
                        subject=commit_info["subject"],
                        body=commit_info["body"],
                    )
                )

                # Extract description from commit messages
                if commit_info["subject"]:
                    descriptions.append(commit_info["subject"])
                if commit_info["body"]:
                    descriptions.append(commit_info["body"])

                # Extract related issues/PRs
                issue_pattern = (
                    r"(?:fixes?|closes?|resolves?)\s+#?(\d+)|(?:#|GH-|GL-)(\d+)"
                )
                matches = re.findall(issue_pattern, commit_info["body"], re.IGNORECASE)
                for match in matches:
                    issue_id = match[0] or match[1]
                    if issue_id:
                        related_issues.append(issue_id)

                # Get branches and tags
                try:
                    branch_list = self.git_utils.get_branches_containing(
                        repo_path, commit_hash
                    )
                    branches.update(branch_list)
                except GitCommandError:
                    pass

                try:
                    tag_list = self.git_utils.get_tags_containing(
                        repo_path, commit_hash
                    )
                    tags.update(tag_list)
                except GitCommandError:
                    pass
            except GitCommandError:
                continue

        # Get changed files (feature_id already sanitized above)
        try:
            changed_files = self.git_utils.log_files(repo_path, feature_id)
            code_paths.update(changed_files)
        except GitCommandError:
            pass

        # Find test files
        test_paths = []
        for code_path in code_paths:
            test_path = self._find_test_file(repo_path, code_path)
            if test_path:
                test_paths.append(test_path)

        # Combine descriptions
        description = " ".join(descriptions[:3]) if descriptions else None

        return FeatureMetadata(
            feature_id=feature_id,
            commits=commits,
            branches=sorted(branches),
            tags=sorted(tags),
            code_paths=sorted(code_paths),
            test_paths=sorted(test_paths),
            description=description,
            related_issues=sorted(set(related_issues)),
        )

    def _find_test_file(self, repo_path: Path, code_path: str) -> str | None:
        """Find test file for a given code path.

        Args:
            repo_path: Repository root path
            code_path: Path to code file

        Returns:
            Path to test file or None
        """
        code_path_obj = Path(code_path)
        base_name = code_path_obj.stem

        # Common test file patterns
        test_patterns = [
            f"test_{base_name}.py",
            f"{base_name}_test.py",
            f"tests/test_{base_name}.py",
            f"tests/{base_name}_test.py",
        ]

        for pattern in test_patterns:
            test_files = self.git_utils.ls_files(repo_path, pattern)
            if test_files:
                return test_files[0]

        return None
