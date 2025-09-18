from claudebot.utils import convert_test_name_to_pytest_path


def test_path():
    assert convert_test_name_to_pytest_path("tests.test_example::test_method") \
           == "tests/test_example.py::test_method"
