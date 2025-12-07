"""Repository manager for handling same-repo and external-repo modes."""

from pathlib import Path
from urllib.parse import urlparse

import requests

from src.shared.config import DocsRepoConfig
from src.shared.errors import (
    GitCommandError,
    InvalidPathError,
)
from src.shared.git_utils import GitUtils
from src.shared.logging import setup_logging

logger = setup_logging()


class RepoManager:
    """Manages repository operations for documentation."""

    def __init__(self, config: DocsRepoConfig):
        """Initialize repository manager.

        Args:
            config: DocsRepoConfig instance
        """
        self.config = config
        self.workspace_root = Path(config.workspace_root)
        self.git_utils = GitUtils(config.workspace_root)

        # Determine repo mode
        self.repo_mode = self._determine_repo_mode()
        self.docs_path = self._get_docs_path()

    def _determine_repo_mode(self) -> str:
        """Determine if we're in same-repo or external-repo mode.

        Returns:
            "same" or "external"
        """
        # For now, default to same-repo mode
        # External repo mode would require additional configuration
        return "same"

    def _get_docs_path(self) -> Path:
        """Get the path to documentation directory.

        Returns:
            Path to docs directory
        """
        # Default docs path in same-repo mode
        docs_path = self.workspace_root / "docs"
        return docs_path

    def suggest_doc_location(
        self, feature_id: str, doc_type: str | None = None
    ) -> tuple[str, str]:
        """Suggest documentation location for a feature.

        Args:
            feature_id: Feature identifier
            doc_type: Optional document type (concept, task, etc.)

        Returns:
            Tuple of (suggested_path, doc_type)
        """
        if not doc_type:
            # Default to concept for now
            doc_type = "concept"

        # Generate path based on doc_type and feature_id
        # Normalize feature_id for filename
        safe_feature_id = feature_id.lower().replace(" ", "_").replace("/", "_")

        if doc_type == "concept":
            path = self.docs_path / "concepts" / f"{safe_feature_id}.md"
        elif doc_type == "task":
            path = self.docs_path / "tasks" / f"{safe_feature_id}.md"
        elif doc_type == "api_reference":
            path = self.docs_path / "api" / f"{safe_feature_id}.md"
        elif doc_type == "release_notes":
            path = self.docs_path / "releases" / f"{safe_feature_id}.md"
        elif doc_type == "feature_overview":
            path = self.docs_path / "features" / f"{safe_feature_id}.md"
        elif doc_type == "configuration_reference":
            path = self.docs_path / "configuration" / f"{safe_feature_id}.md"
        else:
            path = self.docs_path / f"{safe_feature_id}.md"

        return str(path.relative_to(self.workspace_root)), doc_type

    def write_doc(self, path: str, content: str) -> tuple[str, bool, str]:
        """Write documentation file.

        Args:
            path: File path (relative to workspace_root or absolute)
            content: Document content

        Returns:
            Tuple of (actual_path, success, message)

        Raises:
            InvalidPathError: If path is invalid or unsafe
        """
        file_path = Path(path)

        # Resolve path
        if not file_path.is_absolute():
            file_path = self.workspace_root / file_path
        else:
            # Ensure path is within workspace for security
            try:
                file_path.resolve().relative_to(self.workspace_root.resolve())
            except ValueError as e:
                raise InvalidPathError(
                    f"Path outside workspace: {path}",
                    f"File must be within workspace: {self.workspace_root}",
                ) from e

        # Validate path doesn't escape workspace
        if ".." in str(file_path.relative_to(self.workspace_root)):
            raise InvalidPathError(
                f"Invalid path: {path}",
                "Path contains '..' which is not allowed",
            )

        # Create directory structure if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        try:
            file_path.write_text(content, encoding="utf-8")
            relative_path = str(file_path.relative_to(self.workspace_root))
            return relative_path, True, f"Document written to {relative_path}"
        except Exception as e:
            logger.error(f"Error writing document: {e}")
            return str(file_path.relative_to(self.workspace_root)), False, str(e)

    def create_branch(self, branch_name: str) -> bool:
        """Create a git branch.

        Args:
            branch_name: Name of the branch

        Returns:
            True if successful, False otherwise
        """
        try:
            self.git_utils._run_git_command(
                self.workspace_root, "checkout", "-b", branch_name
            )
            return True
        except GitCommandError as e:
            logger.error(f"Error creating branch: {e.message}")
            return False

    def commit_changes(self, message: str, files: list[str] | None = None) -> bool:
        """Commit changes to git.

        Args:
            message: Commit message
            files: Optional list of files to commit (all if None)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add files
            if files:
                for file in files:
                    self.git_utils._run_git_command(self.workspace_root, "add", file)
            else:
                self.git_utils._run_git_command(self.workspace_root, "add", ".")

            # Commit
            self.git_utils._run_git_command(
                self.workspace_root, "commit", "-m", message
            )
            return True
        except GitCommandError as e:
            logger.error(f"Error committing changes: {e.message}")
            return False

    def push_branch(self, branch_name: str) -> bool:
        """Push branch to remote.

        Args:
            branch_name: Name of the branch

        Returns:
            True if successful, False otherwise
        """
        try:
            self.git_utils._run_git_command(
                self.workspace_root, "push", "-u", "origin", branch_name
            )
            return True
        except GitCommandError as e:
            logger.error(f"Error pushing branch: {e.message}")
            return False

    def create_github_pr(
        self, branch: str, title: str, description: str
    ) -> tuple[str | None, int | None, bool, str]:
        """Create a pull request on GitHub.

        Args:
            branch: Branch name
            title: PR title
            description: PR description

        Returns:
            Tuple of (pr_url, pr_number, success, message)
        """
        if not self.config.github_token:
            return None, None, False, "GitHub token not configured"

        # Get repository info
        try:
            remote_url = self.git_utils._run_git_command(
                self.workspace_root, "config", "--get", "remote.origin.url"
            )
            repo_info = self._parse_github_repo(remote_url)
            if not repo_info:
                return None, None, False, "Could not determine GitHub repository"

            owner, repo = repo_info

            # Create PR via GitHub API
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            headers = {
                "Authorization": f"token {self.config.github_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            data = {
                "title": title,
                "body": description,
                "head": branch,
                "base": "main",  # Default base branch
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            pr_data = response.json()
            pr_url = pr_data.get("html_url")
            pr_number = pr_data.get("number")

            return pr_url, pr_number, True, f"PR #{pr_number} created successfully"

        except requests.RequestException as e:
            logger.error(f"Error creating GitHub PR: {e}")
            return None, None, False, f"Failed to create PR: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error creating GitHub PR: {e}")
            return None, None, False, f"Unexpected error: {str(e)}"

    def create_gitlab_pr(
        self, branch: str, title: str, description: str
    ) -> tuple[str | None, int | None, bool, str]:
        """Create a merge request on GitLab.

        Args:
            branch: Branch name
            title: MR title
            description: MR description

        Returns:
            Tuple of (mr_url, mr_number, success, message)
        """
        if not self.config.gitlab_token:
            return None, None, False, "GitLab token not configured"

        # Get repository info
        try:
            remote_url = self.git_utils._run_git_command(
                self.workspace_root, "config", "--get", "remote.origin.url"
            )
            repo_info = self._parse_gitlab_repo(remote_url)
            if not repo_info:
                return None, None, False, "Could not determine GitLab repository"

            project_id = repo_info

            # Create MR via GitLab API
            url = f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests"
            headers = {
                "PRIVATE-TOKEN": self.config.gitlab_token,
            }
            data = {
                "title": title,
                "description": description,
                "source_branch": branch,
                "target_branch": "main",  # Default target branch
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            mr_data = response.json()
            mr_url = mr_data.get("web_url")
            mr_number = mr_data.get("iid")

            return mr_url, mr_number, True, f"MR !{mr_number} created successfully"

        except requests.RequestException as e:
            logger.error(f"Error creating GitLab MR: {e}")
            return None, None, False, f"Failed to create MR: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error creating GitLab MR: {e}")
            return None, None, False, f"Unexpected error: {str(e)}"

    def _parse_github_repo(self, remote_url: str) -> tuple[str, str] | None:
        """Parse GitHub repository from remote URL.

        Args:
            remote_url: Git remote URL

        Returns:
            Tuple of (owner, repo) or None
        """
        # Handle various URL formats
        if remote_url.startswith("git@"):
            # git@github.com:owner/repo.git
            parts = (
                remote_url.replace("git@github.com:", "").replace(".git", "").split("/")
            )
            if len(parts) == 2:
                return (parts[0], parts[1])
        elif remote_url.startswith("https://"):
            # https://github.com/owner/repo.git
            parsed = urlparse(remote_url)
            parts = parsed.path.strip("/").replace(".git", "").split("/")
            if len(parts) == 2:
                return (parts[0], parts[1])

        return None

    def _parse_gitlab_repo(self, remote_url: str) -> str | None:
        """Parse GitLab project ID from remote URL.

        Args:
            remote_url: Git remote URL

        Returns:
            Project ID (URL-encoded) or None
        """
        # Handle various URL formats
        if remote_url.startswith("git@"):
            # git@gitlab.com:owner/repo.git -> owner/repo
            project_path = remote_url.replace("git@gitlab.com:", "").replace(".git", "")
            return project_path.replace("/", "%2F")
        elif remote_url.startswith("https://"):
            # https://gitlab.com/owner/repo.git -> owner/repo
            parsed = urlparse(remote_url)
            project_path = parsed.path.strip("/").replace(".git", "")
            return project_path.replace("/", "%2F")

        return None
