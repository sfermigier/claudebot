# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClaudeBot is an autonomous test fixing bot that uses Claude Code to continuously fix failing tests in Python projects. It operates as a continuous integration tool that:

1. Discovers and runs test suites
2. Randomly selects failing tests to fix
3. Invokes Claude Code with structured prompts
4. Validates fixes and checks for regressions
5. Commits successful fixes and continues the cycle

## Commands

### Running Tests
```bash
uv run pytest tests/ -v                    # Run all tests with verbose output
```

### Running ClaudeBot
```bash
uv run python -m claudebot                 # Run with default settings (tests/ directory)
uv run python -m claudebot tests/ --verbose  # Run with verbose output
uv run python -m claudebot --dry-run       # Discover tests without fixing
uv run python -m claudebot --max-iterations 5  # Limit fix attempts
```

### Package Management
```bash
uv sync              # Install dependencies
uv add <package>     # Add new dependency
uv remove <package>  # Remove dependency
```

## Architecture

### Core Components

- **ClaudeBot**: Main orchestrator class that manages the fixing workflow
- **TestRunner**: Handles test execution and JUnit XML parsing for reliable test result extraction
- **GitManager**: Manages git operations (commits, rollbacks, change detection)
- **TestResult**: Data class representing individual test outcomes

### Key Workflow

1. **Test Discovery**: Uses `uv run pytest` with JUnit XML output for reliable parsing
2. **Test Selection**: Randomly selects from failing tests to avoid patterns
3. **Claude Invocation**: Formats prompts with test context and failure information
4. **Validation**: Verifies the specific test passes and no regressions occur
5. **State Management**: Tracks previously passing tests to detect regressions

### Prompt System

ClaudeBot uses a template-based prompt system:
- Default prompt embedded in `PROMPT_FIX` constant
- Customizable via `--prompt` parameter pointing to external files
- Template variables: `{test_name}` and `{test_output}`

### Safety Features

- **Rollback Mechanism**: Automatically reverts changes if tests fail or regressions occur
- **Regression Detection**: Runs all previously passing tests after each fix
- **Atomic Operations**: Each fix attempt is isolated with proper cleanup

## Development Notes

### Test Path Conversion
The utility function `convert_test_name_to_pytest_path()` converts JUnit XML test names (using dots) to pytest-compatible paths (using slashes). This handles the impedance mismatch between XML output format and pytest execution format.

### Error Handling
ClaudeBot includes robust error handling for:
- Claude Code execution failures
- Test timeouts and subprocess errors
- Git operation failures
- XML parsing errors

The bot continues operation even when individual fix attempts fail, making it resilient for long-running sessions.
