"""Git operations for ClaudeBot."""

import subprocess


class GitError(Exception):
    """Raised when a git operation fails."""

    pass


class GitManager:
    """Manages git operations for ClaudeBot."""

    def get_current_commit(self) -> str:
        """Get the current git commit hash."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        )
        return bool(result.stdout.strip())

    def reset_to_commit(self, commit_hash: str) -> None:
        """Reset to a specific commit, discarding changes."""
        try:
            subprocess.run(
                ["git", "reset", "--hard", commit_hash],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to reset to {commit_hash}") from e

    def commit_changes(self, message: str) -> None:
        """Commit current changes."""
        try:
            # Add all changes
            subprocess.run(
                ["git", "add", "."], capture_output=True, text=True, check=True
            )

            # Commit with message
            subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to commit changes: {e}") from e
