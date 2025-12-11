"""Git utilities for MCP servers."""

import subprocess
from pathlib import Path

from src.shared.errors import GitCommandError, RepositoryNotFoundError
from src.shared.security import SecurityValidator


class GitUtils:
    """Utility class for executing git commands."""

    def __init__(
        self, workspace_root: Path, git_binary: str = "git", timeout: int = 30
    ):
        """Initialize GitUtils.

        Args:
            workspace_root: Root directory containing repositories
            git_binary: Path to git binary (default: "git")
            timeout: Timeout for git commands in seconds (default: 30)
        """
        self.workspace_root = Path(workspace_root)
        self.git_binary = git_binary
        self.timeout = timeout

    def _run_git_command(
        self, repo_path: Path, *args: str, cwd: Path | None = None
    ) -> str:
        """Run a git command and return output.

        Args:
            repo_path: Path to git repository
            *args: Git command arguments
            cwd: Working directory for command (default: repo_path)

        Returns:
            Command output as string

        Raises:
            GitCommandError: If git command fails
            RepositoryNotFoundError: If repository is not found
        """
        repo_path = Path(repo_path)
        if not repo_path.exists():
            raise RepositoryNotFoundError(
                f"Repository not found: {repo_path}",
                f"Ensure the repository exists in workspace: {self.workspace_root}",
            )

        # Check if it's a git repository
        git_dir = repo_path / ".git"
        if not git_dir.exists() and not (repo_path.parent / ".git").exists():
            raise RepositoryNotFoundError(
                f"Not a git repository: {repo_path}",
                "Path does not contain a .git directory",
            )

        cmd = [self.git_binary] + list(args)
        cwd = cwd or repo_path

        try:
            result = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout,
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired as e:
            raise GitCommandError(
                f"Git command timed out: {' '.join(cmd)}",
                f"Command exceeded {self.timeout} second timeout",
            ) from e
        except subprocess.CalledProcessError as e:
            raise GitCommandError(
                f"Git command failed: {' '.join(cmd)}",
                f"Exit code: {e.returncode}, Error: {e.stderr}",
            ) from e

    def log_grep(self, repo_path: Path, pattern: str) -> list[str]:
        """Search git log for commits matching pattern.

        Args:
            repo_path: Path to git repository
            pattern: Pattern to search for in commit messages

        Returns:
            List of commit hashes

        Raises:
            SecurityError: If pattern contains dangerous characters
        """
        # Sanitize pattern to prevent command injection
        pattern = SecurityValidator.sanitize_git_pattern(pattern)
        output = self._run_git_command(
            repo_path, "log", "--grep", pattern, "--format=%H", "--all"
        )
        return [line for line in output.split("\n") if line.strip()]

    def get_commit_info(self, repo_path: Path, commit_hash: str) -> dict[str, str]:
        """Get commit information.

        Args:
            repo_path: Path to git repository
            commit_hash: Commit hash

        Returns:
            Dictionary with commit information

        Raises:
            SecurityError: If commit hash is invalid
        """
        # Validate commit hash to prevent injection
        commit_hash = SecurityValidator.sanitize_commit_hash(commit_hash)
        output = self._run_git_command(
            repo_path,
            "show",
            "-s",
            "--format=%H|%s|%b",
            commit_hash,
        )
        parts = output.split("|", 2)
        return {
            "hash": parts[0] if len(parts) > 0 else commit_hash,
            "subject": parts[1] if len(parts) > 1 else "",
            "body": parts[2] if len(parts) > 2 else "",
        }

    def get_branches_containing(self, repo_path: Path, commit_hash: str) -> list[str]:
        """Get branches containing a commit.

        Args:
            repo_path: Path to git repository
            commit_hash: Commit hash

        Returns:
            List of branch names

        Raises:
            SecurityError: If commit hash is invalid
        """
        # Validate commit hash to prevent injection
        commit_hash = SecurityValidator.sanitize_commit_hash(commit_hash)
        output = self._run_git_command(
            repo_path, "branch", "-a", "--contains", commit_hash
        )
        return [
            line.strip().replace("* ", "").replace("remotes/", "")
            for line in output.split("\n")
            if line.strip()
        ]

    def get_tags_containing(self, repo_path: Path, commit_hash: str) -> list[str]:
        """Get tags containing a commit.

        Args:
            repo_path: Path to git repository
            commit_hash: Commit hash

        Returns:
            List of tag names

        Raises:
            SecurityError: If commit hash is invalid
        """
        # Validate commit hash to prevent injection
        commit_hash = SecurityValidator.sanitize_commit_hash(commit_hash)
        output = self._run_git_command(repo_path, "tag", "--contains", commit_hash)
        return [line.strip() for line in output.split("\n") if line.strip()]

    def diff_files(self, repo_path: Path, base: str, head: str) -> list[str]:
        """Get list of changed files between two commits/branches.

        Args:
            repo_path: Path to git repository
            base: Base commit/branch
            head: Head commit/branch

        Returns:
            List of changed file paths

        Raises:
            SecurityError: If commit hashes are invalid
        """
        # Validate commit hashes to prevent injection
        base = SecurityValidator.sanitize_commit_hash(base)
        head = SecurityValidator.sanitize_commit_hash(head)
        output = self._run_git_command(
            repo_path, "diff", "--name-only", f"{base}..{head}"
        )
        return [line.strip() for line in output.split("\n") if line.strip()]

    def log_files(self, repo_path: Path, pattern: str) -> list[str]:
        """Get files changed in commits matching pattern.

        Args:
            repo_path: Path to git repository
            pattern: Pattern to search for in commit messages

        Returns:
            List of file paths

        Raises:
            SecurityError: If pattern contains dangerous characters
        """
        # Sanitize pattern to prevent command injection
        pattern = SecurityValidator.sanitize_git_pattern(pattern)
        output = self._run_git_command(
            repo_path,
            "log",
            "--grep",
            pattern,
            "--oneline",
            "--name-only",
            "--format=",
            "--all",
        )
        files = set()
        for line in output.split("\n"):
            line = line.strip()
            if line and not line.startswith("commit"):
                files.add(line)
        return sorted(files)

    def ls_files(self, repo_path: Path, pattern: str = "*.py") -> list[str]:
        """List files matching pattern in repository.

        Args:
            repo_path: Path to git repository
            pattern: File pattern (e.g., "test_*.py")

        Returns:
            List of file paths relative to repository root
        """
        output = self._run_git_command(repo_path, "ls-files", pattern)
        return [line.strip() for line in output.split("\n") if line.strip()]

    def get_diff(self, repo_path: Path, base: str, head: str) -> str:
        """Get diff between two commits/branches.

        Args:
            repo_path: Path to git repository
            base: Base commit/branch
            head: Head commit/branch

        Returns:
            Diff output as string

        Raises:
            SecurityError: If commit hashes are invalid
        """
        # Validate commit hashes to prevent injection
        base = SecurityValidator.sanitize_commit_hash(base)
        head = SecurityValidator.sanitize_commit_hash(head)
        return self._run_git_command(repo_path, "diff", f"{base}..{head}")
