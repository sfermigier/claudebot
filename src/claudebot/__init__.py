"""
ClaudeBot - Autonomous Test Fixing Bot

This package continuously fixes failing tests using Claude Code:
1. Runs the full test suite and tracks test status
2. Randomly selects failing tests to fix
3. Uses Claude Code with user-provided prompts
4. Verifies fixes and checks for regressions
5. Commits successful fixes and continues the cycle
"""

from .claudebot import ClaudeBot, main
from .git_manager import GitManager, GitError
from .models import TestResult
from .test_runner import TestRunner
from .utils import convert_test_name_to_pytest_path

__all__ = [
    "ClaudeBot",
    "GitError",
    "GitManager",
    "TestResult",
    "TestRunner",
    "convert_test_name_to_pytest_path",
    "main",
]
