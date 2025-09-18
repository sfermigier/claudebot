"""Utility functions for ClaudeBot."""


def convert_test_name_to_pytest_path(test_name: str) -> str:
    """
    Convert JUnit XML test names to pytest-compatible paths.

    Args:
        test_name: Test name in JUnit XML format (e.g., "tests.test_example::test_method")

    Returns:
        Test path in pytest format (e.g., "tests/test_example.py::test_method")
    """
    # Split on '::' to separate module/class from test function
    parts = test_name.split("::")
    if not parts or len(parts) < 2:
        return test_name  # fallback

    # Replace dots with slashes in the module path, add .py extension
    module_path = parts[0].replace(".", "/") + ".py"
    rest = "::".join(parts[1:])

    return f"{module_path}::{rest}"