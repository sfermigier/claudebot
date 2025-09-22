"""Default prompt generator for test fixing using TestRunner."""

import random
from pathlib import Path

from .test_runner import TestRunner

# Keep this constant prompt template here.
PROMPT_TEMPLATE = """
The following test is currently failing in our Python compiler project.

Please analyze why the test is failing and implement a fix.

Test to fix: {test_name}

Test output:
{test_output}

Steps to follow:
1. Run the failing test to understand the issue: "uv run pytest {test_name} -v"
2. Analyze the failure and identify what needs to be fixed
3. Implement the necessary changes to make the test pass
4. Verify the fix by running the test again
5. Make sure your changes don't break existing functionality

Refer to CLAUDE.md and the docs/plans/ directory for context and guidelines on the project.

Please implement the fix now.
"""


def get_prompts():
    """Generate prompts to fix failing tests using TestRunner."""
    # Use TestRunner to get test results with proper JUnit XML parsing
    test_runner = TestRunner()
    test_results = test_runner.run_full_test_suite(["tests/"], verbose=False)

    # Find failing tests
    failing_tests = [
        result for result in test_results.values() if result.status == "FAILING"
    ]

    if not failing_tests:
        print("All tests are passing!")
        return

    # Randomly select a failing test
    selected_test = random.choice(failing_tests)
    test_name = selected_test.name
    test_output = selected_test.output

    # Use custom prompt from file if available
    prompt_file = Path("prompt-fix.md")
    if prompt_file.exists():
        prompt_template = prompt_file.read_text().strip()
    else:
        prompt_template = PROMPT_TEMPLATE

    prompt = prompt_template.format(
        test_name=test_name, test_output=test_output
    )

    yield {
        "prompt": prompt,
        "description": f"Fix failing test: {test_name}",
    }
