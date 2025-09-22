"""Tests for GitManager using real git repositories in temporary directories."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from claudebot.git_manager import GitError, GitManager


def test_has_uncommitted_changes_with_staged_files(temp_git_repo):
    """Test has_uncommitted_changes with staged but uncommitted files."""
    git_manager = GitManager()

    # Add and stage a new file
    new_file = temp_git_repo / "staged_file.txt"
    new_file.write_text("Staged content\n")
    subprocess.run(["git", "add", "staged_file.txt"], check=True, capture_output=True)

    # Should detect uncommitted changes
    assert git_manager.has_uncommitted_changes()


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        original_cwd = os.getcwd()

        try:
            # Change to temp directory
            os.chdir(repo_path)

            # Initialize git repo
            subprocess.run(
                ["git", "init"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                check=True,
                capture_output=True,
            )

            # Create initial commit
            initial_file = repo_path / "README.md"
            initial_file.write_text("# Test Repository\n")
            subprocess.run(["git", "add", "README.md"], check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                check=True,
                capture_output=True,
            )

            yield repo_path

        finally:
            # Restore original working directory
            os.chdir(original_cwd)


def test_get_current_commit(temp_git_repo):
    """Test getting the current commit hash."""
    git_manager = GitManager()

    # Get commit hash
    commit_hash = git_manager.get_current_commit()

    # Verify it's a valid git hash (40 characters, hexadecimal)
    assert len(commit_hash) == 40
    assert all(c in "0123456789abcdef" for c in commit_hash.lower())

    # Verify it matches what git rev-parse returns directly
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    expected_hash = result.stdout.strip()
    assert commit_hash == expected_hash


def test_has_uncommitted_changes_clean_repo(temp_git_repo):
    """Test has_uncommitted_changes on a clean repository."""
    git_manager = GitManager()

    # Clean repo should have no uncommitted changes
    assert not git_manager.has_uncommitted_changes()


def test_has_uncommitted_changes_with_modifications(temp_git_repo):
    """Test has_uncommitted_changes with file modifications."""
    git_manager = GitManager()

    # Modify an existing file
    readme_file = temp_git_repo / "README.md"
    readme_file.write_text("# Modified Test Repository\n")

    # Should detect uncommitted changes
    assert git_manager.has_uncommitted_changes()


def test_has_uncommitted_changes_with_new_files(temp_git_repo):
    """Test has_uncommitted_changes with new untracked files."""
    git_manager = GitManager()

    # Add a new untracked file
    new_file = temp_git_repo / "new_file.txt"
    new_file.write_text("New content\n")

    # Should detect uncommitted changes
    assert git_manager.has_uncommitted_changes()


def test_commit_changes_with_new_file(temp_git_repo):
    """Test committing changes with a new file."""
    git_manager = GitManager()

    # Add a new file
    new_file = temp_git_repo / "test_file.txt"
    new_file.write_text("Test content\n")

    # Commit the changes
    commit_message = "Add test file"
    git_manager.commit_changes(commit_message)

    # Verify the file was committed
    assert not git_manager.has_uncommitted_changes()

    # Verify the commit message
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%s"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == commit_message


def test_commit_changes_with_modified_file(temp_git_repo):
    """Test committing changes with a modified file."""
    git_manager = GitManager()

    # Modify existing file
    readme_file = temp_git_repo / "README.md"
    original_content = readme_file.read_text()
    readme_file.write_text(original_content + "\nAdditional line\n")

    # Commit the changes
    commit_message = "Update README"
    git_manager.commit_changes(commit_message)

    # Verify changes were committed
    assert not git_manager.has_uncommitted_changes()

    # Verify the commit message
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%s"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == commit_message


def test_commit_changes_no_changes_to_commit(temp_git_repo):
    """Test committing when there are no changes to commit."""
    git_manager = GitManager()

    # Try to commit on a clean repo
    with pytest.raises(GitError) as exc_info:
        git_manager.commit_changes("Nothing to commit")

    assert "Failed to commit changes" in str(exc_info.value)


def test_reset_to_commit(temp_git_repo):
    """Test resetting to a specific commit."""
    git_manager = GitManager()

    # Get initial commit hash
    initial_commit = git_manager.get_current_commit()

    # Make some changes and commit them
    test_file = temp_git_repo / "test_reset.txt"
    test_file.write_text("Content to be reset\n")
    git_manager.commit_changes("Add file for reset test")

    # Verify we're on a different commit
    new_commit = git_manager.get_current_commit()
    assert new_commit != initial_commit
    assert test_file.exists()

    # Reset to initial commit
    git_manager.reset_to_commit(initial_commit)

    # Verify we're back to the initial commit
    current_commit = git_manager.get_current_commit()
    assert current_commit == initial_commit

    # Verify the test file was removed
    assert not test_file.exists()


def test_reset_to_commit_with_uncommitted_changes(temp_git_repo):
    """Test resetting discards committed changes and tracked file modifications."""
    git_manager = GitManager()

    # Get initial commit hash
    initial_commit = git_manager.get_current_commit()

    # Modify existing tracked file (README.md)
    readme_file = temp_git_repo / "README.md"
    original_content = readme_file.read_text()
    readme_file.write_text(original_content + "\nModified content\n")

    # Verify we have uncommitted changes
    assert git_manager.has_uncommitted_changes()

    # Reset to initial commit (should discard modifications to tracked files)
    git_manager.reset_to_commit(initial_commit)

    # Verify tracked file modifications are gone
    assert readme_file.read_text() == original_content


def test_reset_to_commit_with_untracked_files(temp_git_repo):
    """Test that resetting does not remove untracked files (git reset --hard behavior)."""
    git_manager = GitManager()

    # Get initial commit hash
    initial_commit = git_manager.get_current_commit()

    # Add an untracked file
    untracked_file = temp_git_repo / "untracked.txt"
    untracked_file.write_text("Untracked content\n")

    # Verify we have uncommitted changes (untracked file)
    assert git_manager.has_uncommitted_changes()

    # Reset to initial commit
    git_manager.reset_to_commit(initial_commit)

    # Untracked files should still exist (git reset --hard doesn't remove them)
    assert untracked_file.exists()
    # But git still reports it as uncommitted changes
    assert git_manager.has_uncommitted_changes()


def test_reset_to_invalid_commit(temp_git_repo):
    """Test resetting to an invalid commit hash."""
    git_manager = GitManager()

    # Try to reset to an invalid commit hash
    invalid_commit = "invalidhash123"
    with pytest.raises(GitError) as exc_info:
        git_manager.reset_to_commit(invalid_commit)

    assert f"Failed to reset to {invalid_commit}" in str(exc_info.value)


def test_reset_to_nonexistent_commit(temp_git_repo):
    """Test resetting to a valid format but nonexistent commit hash."""
    git_manager = GitManager()

    # Try to reset to a valid format but nonexistent commit hash
    nonexistent_commit = "0000000000000000000000000000000000000000"
    with pytest.raises(GitError) as exc_info:
        git_manager.reset_to_commit(nonexistent_commit)

    assert f"Failed to reset to {nonexistent_commit}" in str(exc_info.value)


def test_integration_workflow(temp_git_repo):
    """Test a complete workflow: check status, commit, reset."""
    git_manager = GitManager()

    # Start with clean repo
    initial_commit = git_manager.get_current_commit()
    assert not git_manager.has_uncommitted_changes()

    # Add some files
    file1 = temp_git_repo / "file1.txt"
    file2 = temp_git_repo / "file2.txt"
    file1.write_text("Content 1\n")
    file2.write_text("Content 2\n")

    # Should have uncommitted changes
    assert git_manager.has_uncommitted_changes()

    # Commit the changes
    git_manager.commit_changes("Add two test files")
    commit_after_add = git_manager.get_current_commit()

    # Should be clean after commit
    assert not git_manager.has_uncommitted_changes()
    assert commit_after_add != initial_commit

    # Modify one file
    file1.write_text("Modified content 1\n")
    assert git_manager.has_uncommitted_changes()

    # Reset back to initial state
    git_manager.reset_to_commit(initial_commit)

    # Should be back to clean initial state
    assert git_manager.get_current_commit() == initial_commit
    assert not git_manager.has_uncommitted_changes()
    assert not file1.exists()
    assert not file2.exists()
