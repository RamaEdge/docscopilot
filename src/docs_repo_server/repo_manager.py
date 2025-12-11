"""Repository manager for handling same-repo and external-repo modes."""

import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.shared.config import DocsRepoConfig
from src.shared.errors import (
    APIError,
    ErrorCode,
    GitCommandError,
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
        self.git_utils = GitUtils(
            config.workspace_root, timeout=config.git_command_timeout
        )

        # Create secure HTTP session with certificate verification
        self.session = requests.Session()
        retry_config = config.api_retry
        retry_strategy = Retry(
            total=retry_config.total,
            backoff_factor=retry_config.backoff_factor,
            status_forcelist=retry_config.status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Determine repo mode
        self.repo_mode = config.repo_mode
        self.docs_path = self._get_docs_path()

    def _get_docs_path(self) -> Path:
        """Get the path to documentation directory.

        Returns:
            Path to docs directory
        """
        # Use configured docs directory name
        docs_path = self.workspace_root / self.config.docs_directory
        return docs_path

    def suggest_doc_location(
        self, feature_id: str, doc_type: str | None = None
    ) -> tuple[str, str]:
        """Suggest documentation location for a feature.

        Args:
            feature_id: Feature identifier (must be validated)
            doc_type: Optional document type (concept, task, etc.)

        Returns:
            Tuple of (suggested_path, doc_type)
        """
        # Validate doc_type if provided, otherwise use default from config
        if doc_type:
            doc_type = SecurityValidator.validate_doc_type(doc_type)
        else:
            doc_type = self.config.default_doc_type

        # Generate path based on doc_type and feature_id
        # Normalize feature_id for filename (already validated)
        safe_feature_id = feature_id.lower().replace(" ", "_").replace("/", "_")

        # Get directory name from config mapping, fallback to doc_type if not mapped
        directory = self.config.doc_type_directories.get(doc_type, doc_type)
        path = self.docs_path / directory / f"{safe_feature_id}.md"

        return str(path.relative_to(self.workspace_root)), doc_type

    def generate_branch_name(
        self,
        title: str,
        feature_id: str | None = None,
        ensure_unique: bool = True,
    ) -> str:
        """Generate a git branch name from available context.

        Args:
            title: PR title
            feature_id: Optional feature identifier (takes priority if provided)
            ensure_unique: Check if branch exists and make unique if needed

        Returns:
            Valid git branch name
        """
        # Priority: feature_id > title > timestamp fallback
        if feature_id:
            base = self._sanitize_for_branch(feature_id)
        else:
            base = self._sanitize_for_branch(title)

        # Build branch name with docs/ prefix
        if base:
            branch_name = f"docs/{base}"
        else:
            # Fallback to timestamp if both title and feature_id are empty/invalid
            branch_name = f"docs/{int(time.time())}"

        # Ensure it's valid according to Git rules
        branch_name = self._ensure_valid_branch_name(branch_name)

        # Make unique if needed
        if ensure_unique:
            branch_name = self._ensure_unique_branch(branch_name)

        return branch_name

    def _sanitize_for_branch(self, text: str) -> str:
        """Sanitize text for use in branch name.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized branch name segment
        """
        if not text:
            return ""

        # Lowercase
        text = text.lower()

        # Replace spaces, underscores, and slashes with hyphens
        text = re.sub(r"[\s_/]+", "-", text)

        # Remove invalid characters (keep alphanumeric and hyphens)
        text = re.sub(r"[^a-z0-9\-]", "", text)

        # Remove multiple consecutive hyphens
        text = re.sub(r"-+", "-", text)

        # Remove leading/trailing hyphens
        text = text.strip("-")

        # Limit length (leave room for prefix and uniqueness suffix)
        if len(text) > 200:
            text = text[:200]

        return text

    def _ensure_valid_branch_name(self, name: str) -> str:
        """Ensure branch name follows Git rules.

        Args:
            name: Branch name to validate

        Returns:
            Valid branch name
        """
        # Can't start/end with dot
        name = name.strip(".")

        # Can't end with .lock
        if name.endswith(".lock"):
            name = name[:-5]

        # Can't contain ..
        name = name.replace("..", "-")

        # Can't contain @{
        name = name.replace("@", "-")
        name = name.replace("{", "-")

        # Ensure it doesn't exceed Git's 255 character limit
        if len(name) > 255:
            name = name[:255]

        return name

    def _ensure_unique_branch(self, base_name: str) -> str:
        """Ensure branch name is unique by appending number if needed.

        Args:
            base_name: Base branch name

        Returns:
            Unique branch name
        """
        # Check if branch exists
        try:
            branches_output = self.git_utils._run_git_command(
                self.workspace_root, "branch", "-a"
            )
            existing_branches = [
                b.strip().replace("* ", "").replace("remotes/", "")
                for b in branches_output.split("\n")
                if b.strip()
            ]

            # Extract just the branch name (without remote prefix)
            existing_branch_names = set()
            for branch in existing_branches:
                # Handle remotes/origin/branch-name format
                if "/" in branch:
                    existing_branch_names.add(branch.split("/")[-1])
                else:
                    existing_branch_names.add(branch)

            if base_name not in existing_branch_names:
                return base_name

            # Append number to make unique
            counter = 1
            while counter <= 1000:  # Safety limit
                candidate = f"{base_name}-{counter}"
                if candidate not in existing_branch_names:
                    return candidate
                counter += 1

            # Fallback to timestamp if counter exceeds limit
            timestamp = int(time.time())
            return f"{base_name}-{timestamp}"

        except Exception as e:
            # If check fails, return base name
            logger.warning(f"Could not check branch uniqueness: {e}")
            return base_name

    def write_doc(self, path: str, content: str) -> tuple[str, bool, str]:
        """Write documentation file.

        Args:
            path: File path (relative to workspace_root or absolute, must be validated)
            content: Document content

        Returns:
            Tuple of (actual_path, success, message)

        Raises:
            InvalidPathError: If path is invalid or unsafe
        """
        # Path should already be validated, but double-check for safety
        file_path = SecurityValidator.validate_path(path, self.workspace_root)

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
            branch_name: Name of the branch (must be validated)

        Returns:
            True if successful, False otherwise
        """
        # Branch name should already be validated, but ensure it's safe
        branch_name = SecurityValidator.validate_branch_name(branch_name)
        try:
            # Validate branch name
            validated_name = validate_branch_name(branch_name)
            self.git_utils._run_git_command(
                self.workspace_root, "checkout", "-b", validated_name
            )
            return True
        except (GitCommandError, InvalidPathError) as e:
            logger.error(f"Error creating branch: {e.message}")
            return False

    def commit_changes(self, message: str, files: list[str] | None = None) -> bool:
        """Commit changes to git.

        Args:
            message: Commit message
            files: Optional list of files to commit (all if None, paths must be validated)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add files
            if files:
                for file in files:
                    # Validate file path
                    validated_path = SecurityValidator.validate_path(
                        file, self.workspace_root
                    )
                    relative_path = str(validated_path.relative_to(self.workspace_root))
                    self.git_utils._run_git_command(
                        self.workspace_root, "add", relative_path
                    )
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

    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        retryable_exceptions=(RequestException, Timeout),
    )
    def _create_github_pr_request(
        self, url: str, headers: dict[str, str], data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make GitHub API request with retry logic.

        Args:
            url: API endpoint URL
            headers: Request headers
            data: Request payload

        Returns:
            Response JSON data

        Raises:
            APIError: If request fails after retries
        """
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except Timeout as e:
            raise APIError(
                "GitHub API request timed out",
                details=str(e),
                error_code=ErrorCode.API_TIMEOUT,
            ) from e
        except requests.HTTPError as e:
            if e.response and e.response.status_code == 401:
                raise APIError(
                    "GitHub authentication failed",
                    details=str(e),
                    error_code=ErrorCode.API_AUTHENTICATION_FAILED,
                ) from e
            elif e.response and e.response.status_code == 403:
                raise APIError(
                    "GitHub API rate limit exceeded",
                    details=str(e),
                    error_code=ErrorCode.API_RATE_LIMIT,
                ) from e
            raise APIError(
                f"GitHub API request failed: {e.response.status_code if e.response else 'Unknown'}",
                details=str(e),
                error_code=ErrorCode.API_REQUEST_FAILED,
            ) from e

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

            # Create PR via GitHub API (supports GitHub Enterprise)
            url = f"{self.config.github_api_base_url}/repos/{owner}/{repo}/pulls"
            headers = {
                "Authorization": f"token {self.config.github_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            data = {
                "title": title,
                "body": description,
                "head": branch,
                "base": self.config.default_base_branch,
            }

            # Use secure session with certificate verification
            response = self.session.post(
                url,
                headers=headers,
                json=data,
                timeout=self.config.api_request_timeout,
                verify=True,
            )
            response.raise_for_status()

            pr_data = response.json()
            pr_url = pr_data.get("html_url")
            pr_number = pr_data.get("number")

            return pr_url, pr_number, True, f"PR #{pr_number} created successfully"

        except APIError as e:
            logger.error(f"Error creating GitHub PR: {e.message}")
            return None, None, False, e.message
        except Exception as e:
            logger.error(f"Unexpected error creating GitHub PR: {e}")
            return None, None, False, f"Unexpected error: {str(e)}"

    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        retryable_exceptions=(RequestException, Timeout),
    )
    def _create_gitlab_pr_request(
        self, url: str, headers: dict[str, str], data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make GitLab API request with retry logic.

        Args:
            url: API endpoint URL
            headers: Request headers
            data: Request payload

        Returns:
            Response JSON data

        Raises:
            APIError: If request fails after retries
        """
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except Timeout as e:
            raise APIError(
                "GitLab API request timed out",
                details=str(e),
                error_code=ErrorCode.API_TIMEOUT,
            ) from e
        except requests.HTTPError as e:
            if e.response and e.response.status_code == 401:
                raise APIError(
                    "GitLab authentication failed",
                    details=str(e),
                    error_code=ErrorCode.API_AUTHENTICATION_FAILED,
                ) from e
            elif e.response and e.response.status_code == 429:
                raise APIError(
                    "GitLab API rate limit exceeded",
                    details=str(e),
                    error_code=ErrorCode.API_RATE_LIMIT,
                ) from e
            raise APIError(
                f"GitLab API request failed: {e.response.status_code if e.response else 'Unknown'}",
                details=str(e),
                error_code=ErrorCode.API_REQUEST_FAILED,
            ) from e

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

            # Create MR via GitLab API (supports self-hosted GitLab)
            url = f"{self.config.gitlab_api_base_url}/projects/{project_id}/merge_requests"
            headers = {
                "PRIVATE-TOKEN": self.config.gitlab_token,
            }
            data = {
                "title": title,
                "description": description,
                "source_branch": branch,
                "target_branch": self.config.default_base_branch,
            }

            # Use secure session with certificate verification
            response = self.session.post(
                url,
                headers=headers,
                json=data,
                timeout=self.config.api_request_timeout,
                verify=True,
            )
            response.raise_for_status()

            mr_data = response.json()
            mr_url = mr_data.get("web_url")
            mr_number = mr_data.get("iid")

            return mr_url, mr_number, True, f"MR !{mr_number} created successfully"

        except APIError as e:
            logger.error(f"Error creating GitLab MR: {e.message}")
            return None, None, False, e.message
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
        github_host = self.config.github_host
        # Handle various URL formats
        if remote_url.startswith(f"git@{github_host}:"):
            # git@github.com:owner/repo.git (or git@custom-host:owner/repo.git)
            parts = (
                remote_url.replace(f"git@{github_host}:", "")
                .replace(".git", "")
                .split("/")
            )
            if len(parts) == 2:
                return (parts[0], parts[1])
        elif remote_url.startswith("https://"):
            # https://github.com/owner/repo.git (or https://custom-host/owner/repo.git)
            parsed = urlparse(remote_url)
            if github_host in parsed.netloc or parsed.netloc.endswith(github_host):
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
        gitlab_host = self.config.gitlab_host
        # Handle various URL formats
        if remote_url.startswith(f"git@{gitlab_host}:"):
            # git@gitlab.com:owner/repo.git -> owner/repo (or custom host)
            project_path = remote_url.replace(f"git@{gitlab_host}:", "").replace(
                ".git", ""
            )
            return project_path.replace("/", "%2F")
        elif remote_url.startswith("https://"):
            # https://gitlab.com/owner/repo.git -> owner/repo (or custom host)
            parsed = urlparse(remote_url)
            if gitlab_host in parsed.netloc or parsed.netloc.endswith(gitlab_host):
                project_path = parsed.path.strip("/").replace(".git", "")
                return project_path.replace("/", "%2F")

        return None
