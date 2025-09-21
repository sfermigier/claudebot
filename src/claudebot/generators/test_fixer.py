"""Test fixer prompt generator - reproduces current ClaudeBot behavior."""

import random
from typing import Dict
from collections.abc import Iterator
from ..prompt_generator import PromptGenerator, PromptRequest
from ..models import TestResult

DEFAULT_PROMPT_TEMPLATE = """
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


class TestFixerGenerator(PromptGenerator):
    """Generates prompts to fix failing tests one by one."""

    def __init__(self, prompt_template: str = DEFAULT_PROMPT_TEMPLATE):
        self.prompt_template = prompt_template.strip()

    def get_prompts(
        self, test_results: Dict[str, TestResult], **kwargs
    ) -> Iterator[PromptRequest]:
        """Generate prompts for fixing failing tests."""
        failing_tests = [
            name for name, result in test_results.items() if result.status == "FAILING"
        ]

        if not failing_tests:
            return

        # Randomly select a failing test (same as current behavior)
        test_name = random.choice(failing_tests)
        test_result = test_results[test_name]

        prompt = self.prompt_template.format(
            test_name=test_name, test_output=test_result.output
        )

        yield PromptRequest(
            prompt=prompt,
            description=f"Fix failing test: {test_name}",
            context={
                "test_name": test_name,
                "test_output": test_result.output,
                "generator_type": "test_fixer",
            },
        )

    def should_continue(self, test_results: Dict[str, TestResult]) -> bool:
        """Continue while there are failing tests."""
        failing_count = sum(
            1 for result in test_results.values() if result.status == "FAILING"
        )
        return failing_count > 0

    def on_prompt_completed(
        self, request: PromptRequest, success: bool, test_results: Dict[str, TestResult]
    ) -> None:
        """Handle completion of a test fix attempt."""
        test_name = request.context.get("test_name")
        if success and test_name:
            print(f"🎊 Successfully fixed test: {test_name}")
        elif test_name:
            print(f"💔 Failed to fix test: {test_name}")


def get_prompts(
    test_results: Dict[str, TestResult], **kwargs
) -> Iterator[PromptRequest]:
    """Entry point function for module-based loading."""
    generator = TestFixerGenerator()
    yield from generator.get_prompts(test_results, **kwargs)
