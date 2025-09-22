#!/usr/bin/env python3
"""
Example prompt generator module for test fixing.
"""

import subprocess
import random

TEST_FIX_PROMPT_TEMPLATE = """
This is a custom prompt generator example.

Test to fix: {test_name}

Error output:
{test_output}

Please fix this test by analyzing the error and implementing the necessary changes.
"""


def get_prompts():
    """Generate prompts to fix failing tests."""
    # Run pytest to get failing tests
    result = subprocess.run(
        ["uv", "run", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True, check=False,
    )

    if result.returncode == 0:
        print("All tests are passing!")
        return

    # Parse output to find failing tests (simple approach)
    lines = result.stdout.split("\n")
    failing_tests = []
    for line in lines:
        if "FAILED" in line:
            # Extract test name from line like "tests/test_example.py::test_method FAILED"
            test_name = line.split(" ")[0]
            failing_tests.append(test_name)

    if not failing_tests:
        return

    # Pick a random failing test
    test_name = random.choice(failing_tests)

    prompt = TEST_FIX_PROMPT_TEMPLATE.format(
        test_name=test_name,
        test_output=result.stdout
    )

    yield {
        "prompt": prompt,
        "description": f"Custom fix for test: {test_name}",
    }
