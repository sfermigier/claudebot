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

---


## 1. Core Development Philosophy

These overarching principles guide our approach to building software.

*   **Simplicity and Readability**: Write simple, straightforward code that is easy to understand and maintain. Prioritize clarity over cleverness.
*   **No Duplication (DRY)**: Don't repeat yourself. Every piece of knowledge should have a single, unambiguous representation.
*   **Reveals Intention**: Use expressive names and small, focused functions to make the code's purpose clear.
*   **Minimalism**: Keep the design minimal by removing unnecessary code, classes, and complexity. Less code means less debt.
*   **Single Responsibility**: Ensure functions and classes have a single, well-defined purpose.
*   **Functional Core, Imperative Shell**: Isolate side-effects (like I/O and state changes) at the application's edges. Keep the core logic pure, immutable, and predictable.
*   **Performance**: Consider performance without sacrificing readability.

Adopt the 4 Rules of Simple Design:

- **Passes all tests:** First, ensure the code is correct and works as proven by a comprehensive test suite.
- **Reveals intention:** Write expressive code that is clear and easy to understand through good naming and small functions.
- **No duplication:** Eliminate redundancy by ensuring every piece of knowledge has a single, unambiguous representation (DRY).
- **Fewest elements:** Keep the design minimal by removing any unnecessary code, classes, or complexity.

## 2. Code Organization & Architecture

*   **Project Structure**: For larger projects, use a `src` directory to keep import paths clean.
    ```
    my_project/
    ├── docs/
    ├── src/
    │   └── my_project/
    │       ├── __init__.py
    │       ├── main.py
    │       └── utils.py
    ├── tests/
    ├── pyproject.toml
    └── README.md
    ```
*   **Onion Architecture**: For complex applications, separate concerns into distinct layers (Domain, Application, Infrastructure, Presentation) to promote loose coupling and high cohesion.
*   **Function Ordering**: In each module, define main functions and classes at the top (top-down), unless constrained otherwise.

## 3. Coding Best Practices

### Style and Formatting

*   **PEP 8**: Adhere to PEP 8 for naming conventions:
    *   `snake_case` for functions, variables, and modules.
    *   `PascalCase` for classes.
    *   `UPPER_SNAKE_CASE` for constants.
*   **Line Length**: Maximum of 88 characters.
*   **F-strings**: Use f-strings for string formatting, but not for logging.
*   **Descriptive Names**: Use clear and meaningful names for variables and functions (e.g., prefix handlers with "handle").

### Functional and Imperative Code

*   **Immutability**: Prefer immutable data structures like `tuples` and `frozenset`. Instead of modifying a collection in place, create a new one.
*   **Small, Pure Functions**: Write small, deterministic functions with clear inputs and outputs, avoiding side effects.
*   **Avoid Modifying Parameters**: Do not modify objects passed as parameters unless that is the function's explicit purpose.
*   **Early Returns**: Use early returns to reduce nested conditional logic.
*   **Command-Quey Separation (CQS)**: every method should either be a command that performs an action, or a query that returns data to the caller, but not both. In other words, asking a question should not change the answer. More formally, methods should return a value only if they are referentially transparent and hence possess no side effects.
* **Leverage Exceptions**: don't return a boolean to report success or failure of an operation. Raise an exception.

### Comments and Documentation

*   **Docstrings**: All public APIs (modules, functions, classes, and methods) must have docstrings following PEP 257 conventions.
*   **Explain the "Why"**: Use comments to explain the reasoning behind non-obvious code, not to describe *what* the code does.
*   **TODO Comments**: Mark issues in existing code with a `TODO:` prefix.

### Error Handling

*   **Be Specific**: Catch specific exceptions rather than using a bare `except:`.
*   **Custom Exceptions**: Define custom exception classes for application-specific errors.
*   **Exception Chaining**: Use `raise NewException from original_exception` to preserve the original traceback.
*   **Avoid Exceptions for Control Flow**: Exceptions should be for exceptional circumstances, not normal program flow.

### Other Best Practices

*   **Avoid Magic Values**: Use named constants instead of hardcoded strings or numbers.
*   **Build Iteratively**: Start with minimal functionality, verify it works, and then add complexity.
*   **Clean Logic**: Keep core logic clean and push implementation details to the edges.

## 4. Python-Specific Guidelines

### Type Hinting

*   **Mandatory Type Hints**: Type hints are required for all function signatures to improve clarity and enable static analysis.
*   **Modern Syntax**: Prefer built-in generic types (e.g., `list[str]`) over aliases from the `typing` module (e.g., `List[str]`).
*   **Optional Types**: Use `X | None` for values that can be `None` and perform explicit `None` checks.

### Asynchronous Code

*   **Async/Await**: Use `async`/`await` for I/O-bound operations.
*   **Testing**: Use `anyio` for testing asynchronous code, not `asyncio`.
*   **Avoid Blocking**: Be mindful of long-running synchronous code within an `async` function, as it can block the event loop.

### Dependencies and Data Structures

*   **HTTP Requests**: Prefer `httpx` over `requests`.
*   **Data Structures**:
    *   Use `tuples` for heterogeneous, immutable data.
    *   Use `lists` for homogeneous, mutable data.
    *   Use `sets` for unordered collections of unique elements.

## 5. Tooling and Workflow

### Package Management

*   **Use `uv` exclusively**:
    *   **Installation**: `uv add <package>`
    *   **Running tools**: `uv run <tool>`
    *   **Forbidden**: Do not use `uv pip install` or the `@latest` syntax.

### Code Quality and Formatting

*   **Ruff**: Use `ruff` for formatting, linting, and import sorting.
    *   **Format**: `uv run ruff format .`
    *   **Check and Fix**: `uv run ruff check . --fix`
*   **Type Checking**: Use `pyrefly` for static type checking.
    *   **Run**: `uv run pyrefly`
*   **Pre-commit**: A `.pre-commit-config.yaml` is configured to run tools like Ruff and Prettier on every commit.

### Testing

*   **Framework**: Use `pytest`. Tests are located in the `tests/` directory.
    *   **Run tests**: `uv run pytest`
*   **Test Coverage**:
    *   New features require tests.
    *   Bug fixes require regression tests.
    *   Ensure edge cases and error conditions are tested.
*   **Test Philosophy**:
    *   **Avoid Mocks**: Prefer stubs. Whenever possible, verify a tangible outcome (state) rather than an internal interaction (behavior).
    *   **Realistic Inputs**: Test your code with realistic inputs and validate the outputs.
    * Organise tests using pytest modules and functions. Do now not use specific classes ("TestSomething"). Use fixtures as needed.
    * Don't catch exceptions in tests. Let pytest catch and report exception.
    * Use `with pytest.raises(...)` to test that an exception occurs.
    * Do not print anything during tests.

### Git Workflow

*   **Feature Branches**: Always work on feature branches, never commit directly to `main`.
    *   **Branch Naming**: Use descriptive names like `fix/auth-timeout` or `feat/api-pagination`.
*   **Atomic Commits**: Each commit should represent a single logical change.
*   **Conventional Commits**: Use the conventional commit style: `type(scope): short description`.
    *   Examples: `feat(eval): add new metrics`, `fix(cli): correct help message`.
*   **Commit Message Content**: Never include `co-authored-by` or mention the tool used to create the commit message.
* **Squash on Merge**: The original guidelines specified to squash commits only when merging to main. This strategy maintains a clean, linear history on the main branch while preserving the detailed, incremental history on feature branches during development and review.

### Error Resolution

1. Common Issues
   - Type errors:
     - Get full line context
     - Check Optional types
     - Add type narrowing
     - Verify function signatures
   - Line length:
     - Break strings with parentheses
     - Multi-line function calls
     - Split imports
   - Types:
     - Add None checks
     - Narrow string types
     - Match existing patterns

2. Best Practices
   - Check git status before commits
   - Run formatters before type checks
   - Keep changes minimal
   - Follow existing patterns
   - Document public APIs
   - Test thoroughly
