# """
# ClaudeBot - Autonomous Task Execution Bot
#
# This package continuously executes tasks using Claude Code:
# 1. Loads custom prompt generators
# 2. Generates prompts based on current state
# 3. Executes prompts with Claude Code
# 4. Repeats in a continuous loop
# 5. Supports any custom task via generator functions
# """
#
# from .claudebot import ClaudeBot
# from .cli import main
# from .git_manager import GitManager, GitError
# from .run_tests import TestRunner
# from .utils import convert_test_name_to_pytest_path
#
# __all__ = [
#     "ClaudeBot",
#     "GitError",
#     "GitManager",
#     "TestRunner",
#     "convert_test_name_to_pytest_path",
#     "main",
# ]
