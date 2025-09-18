from claudebot.utils import convert_test_name_to_pytest_path


def test_path_with_dots():
    """Test conversion when module path contains dots."""
    assert (
        convert_test_name_to_pytest_path("tests.test_example::test_method")
        == "tests/test_example.py::test_method"
    )


def test_path_without_dots():
    """Test conversion when module path doesn't contain dots (assumes tests/ directory)."""
    assert (
        convert_test_name_to_pytest_path(
            "test_arm64_all::test_compiles_to_executable[_bfmandel]"
        )
        == "tests/test_arm64_all.py::test_compiles_to_executable[_bfmandel]"
    )
