"""Utility functions for ClaudeBot."""


def convert_test_name_to_pytest_path(test_name: str) -> str:
    """
    Convert JUnit XML test names to pytest-compatible paths.

    Args:
        test_name: Test name in JUnit XML format (e.g., "tests.test_example::test_method" or "test_example::test_method")

    Returns:
        Test path in pytest format (e.g., "tests/test_example.py::test_method")
    """
    # Split on '::' to separate module/class from test function
    parts = test_name.split("::")
    if not parts or len(parts) < 2:
        return test_name  # fallback

    module_part = parts[0]
    rest = "::".join(parts[1:])

    # If module already contains dots, convert them to slashes (e.g., "tests.test_example")
    if "." in module_part:
        module_path = module_part.replace(".", "/") + ".py"
    else:
        # If no dots, assume it's a test file that should be in tests/ directory
        module_path = f"tests/{module_part}.py"

    return f"{module_path}::{rest}"
