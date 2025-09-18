#!/usr/bin/env python3
"""
ClaudeBot - Autonomous Test Fixing Bot

This script continuously fixes failing tests using Claude Code:
1. Runs the full test suite and tracks test status
2. Randomly selects failing tests to fix
3. Uses Claude Code with user-provided prompts
4. Verifies fixes and checks for regressions
5. Commits successful fixes and continues the cycle
"""

import subprocess
import sys
import time
import random
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass

PROMPT_FIX = """
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


def main():
    """Main function with command line argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="ClaudeBot - Autonomous test fixing with Claude Code"
    )
    parser.add_argument(
        "test_paths",
        nargs="*",
        default=["tests/"],
        help="Test paths or patterns to include (default: tests/)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="prompt-fix.md",
        help="Prompt template file (default: prompt-fix.md)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of fix attempts (default: unlimited)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=60,
        help="Delay between test fixes in seconds (default: 60)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Just discover and report test status, don't fix anything",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose output with detailed progress information",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Show debug output including prompts sent to Claude",
    )

    args = parser.parse_args()

    # Create and run ClaudeBot
    bot = ClaudeBot(
        args.test_paths, args.prompt, verbose=args.verbose, debug=args.debug
    )

    if args.dry_run:
        print("🔍 DRY RUN MODE - Just discovering tests")
        bot.discover_and_run_tests()
        print("\n✅ Dry run complete")
    else:
        bot.run_continuous_fixing(
            max_iterations=args.max_iterations, delay_between_tests=args.delay
        )


@dataclass
class TestResult:
    """Represents the result of a single test."""

    name: str
    status: str  # "PASSING" or "FAILING"
    output: str = ""


class GitManager:
    """Manages git operations for ClaudeBot."""

    def get_current_commit(self) -> str:
        """Get the current git commit hash."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        )
        return bool(result.stdout.strip())

    def reset_to_commit(self, commit_hash: str) -> bool:
        """Reset to a specific commit, discarding changes."""
        try:
            subprocess.run(
                ["git", "reset", "--hard", commit_hash],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to reset to {commit_hash}: {e}")
            return False

    def commit_changes(self, message: str) -> bool:
        """Commit current changes."""
        try:
            # Add all changes
            subprocess.run(
                ["git", "add", "."], capture_output=True, text=True, check=True
            )

            # Commit with message
            subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to commit changes: {e}")
            return False


class TestRunner:
    """Manages test execution and result parsing."""

    def run_full_test_suite(
        self, test_paths: List[str], timeout: int = 600, verbose: bool = False
    ) -> Dict[str, TestResult]:
        """
        Run the full test suite and return test results.

        Args:
            test_paths: List of test paths/patterns to run
            timeout: Timeout in seconds
            verbose: Whether to show verbose output

        Returns:
            Dictionary mapping test names to TestResult objects
        """
        print("🧪 Running full test suite...")

        # Create temp file in tmp/ directory (not /tmp/)
        tmp_dir = Path("tmp")
        tmp_dir.mkdir(exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", dir=tmp_dir, delete=False
        ) as temp_file:
            xml_file = temp_file.name

        try:
            # Run pytest with verbose output and JUnit XML for parsing
            cmd = (
                ["uv", "run", "pytest"]
                + test_paths
                + ["-v", "--tb=short", f"--junit-xml={xml_file}"]
            )

            if verbose:
                print(f"🔧 Running command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )

            if verbose:
                print(f"📊 Test command exit code: {result.returncode}")
                if result.stdout:
                    print(f"📝 Test stdout: {result.stdout[:500]}...")
                if result.stderr:
                    print(f"⚠️ Test stderr: {result.stderr[:500]}...")

            # Parse the JUnit XML file for reliable test results
            return self._parse_junit_xml(xml_file, verbose)

        except subprocess.TimeoutExpired:
            print(f"⚠️ Test suite timed out after {timeout} seconds")
            return {}
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Test suite execution had issues: {e}")
            # Still try to parse XML if it exists
            return self._parse_junit_xml(xml_file, verbose)
        finally:
            # Clean up temp file
            try:
                Path(xml_file).unlink(missing_ok=True)
            except Exception:
                pass  # Ignore cleanup errors

    def run_single_test(self, test_name: str, timeout: int = 60) -> TestResult:
        """
        Run a single test and return its result.

        Args:
            test_name: Name of the test to run
            timeout: Timeout in seconds

        Returns:
            TestResult object
        """


        test_path = convert_test_name_to_pytest_path(test_name)

        try:

            result = subprocess.run(
                ["uv", "run", "pytest", test_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            status = "PASSING" if result.returncode == 0 else "FAILING"
            output = result.stdout + result.stderr

            return TestResult(name=test_name, status=status, output=output)

        except subprocess.TimeoutExpired:
            return TestResult(
                name=test_name,
                status="FAILING",
                output=f"Test timed out after {timeout} seconds",
            )
        except subprocess.CalledProcessError as e:
            return TestResult(name=test_name, status="FAILING", output=str(e))

    def _parse_junit_xml(
        self, xml_file: str, verbose: bool = False
    ) -> Dict[str, TestResult]:
        """
        Parse JUnit XML file to extract test results.

        Args:
            xml_file: Path to the JUnit XML file
            verbose: Whether to show verbose parsing output

        Returns:
            Dictionary mapping test names to TestResult objects
        """
        results = {}

        try:
            if not Path(xml_file).exists():
                if verbose:
                    print(f"⚠️ JUnit XML file not found: {xml_file}")
                return {}

            tree = ET.parse(xml_file)
            root = tree.getroot()

            if verbose:
                print(
                    f"📊 Parsing JUnit XML with {len(root.findall('.//testcase'))} test cases"
                )

            for testcase in root.findall(".//testcase"):
                classname = testcase.get("classname", "")
                name = testcase.get("name", "")

                # Build full test name like pytest does: file::class::method or file::method
                if classname and name:
                    test_name = f"{classname}::{name}"
                elif name:
                    test_name = name
                else:
                    continue

                # Check for failure/error/skip elements
                failure = testcase.find("failure")
                error = testcase.find("error")
                skipped = testcase.find("skipped")

                if failure is not None or error is not None:
                    status = "FAILING"
                    output = ""
                    if failure is not None:
                        output = failure.text or failure.get("message", "")
                    elif error is not None:
                        output = error.text or error.get("message", "")
                elif skipped is not None:
                    status = "SKIPPED"
                    output = skipped.text or skipped.get("message", "")
                else:
                    status = "PASSING"
                    output = ""

                results[test_name] = TestResult(
                    name=test_name, status=status, output=output
                )

                if verbose and len(results) <= 5:  # Show details for first few tests
                    print(f"   📝 {test_name}: {status}")

            if verbose:
                print(f"✅ Parsed {len(results)} test results from JUnit XML")

        except ET.ParseError as e:
            print(f"❌ Failed to parse JUnit XML: {e}")
        except Exception as e:
            print(f"❌ Error reading JUnit XML file: {e}")

        return results

    def _parse_pytest_output(self, output: str) -> Dict[str, TestResult]:
        """
        Fallback parser for pytest output (deprecated - use JUnit XML instead).
        """
        results = {}
        lines = output.split("\n")

        for line in lines:
            line = line.strip()

            # Look for test result lines like:
            # tests/test_example.py::test_function PASSED
            # tests/test_example.py::test_function FAILED
            if "::" in line and (" PASSED" in line or " FAILED" in line):
                parts = line.split()
                if len(parts) >= 2:
                    test_name = parts[0]
                    if " PASSED" in line:
                        status = "PASSING"
                    elif " FAILED" in line:
                        status = "FAILING"
                    else:
                        continue

                    results[test_name] = TestResult(name=test_name, status=status)

        return results


class ClaudeBot:
    """Main ClaudeBot class for autonomous test fixing."""

    def __init__(
        self,
        test_paths: List[str],
        prompt_file: str = "prompt-fix.md",
        verbose: bool = False,
        debug: bool = False,
    ):
        self.test_paths = test_paths
        self.prompt_file = Path(prompt_file)
        self.verbose = verbose
        self.debug = debug
        self.git_manager = GitManager()
        self.test_runner = TestRunner()

        # Load the prompt template
        if self.prompt_file.exists():
            self.prompt_template = self.prompt_file.read_text()
        else:
            print(
                f"⚠️ Warning: Prompt file {prompt_file} not found, using default prompt"
            )
            self.prompt_template = self._get_default_prompt()

        # Test state tracking
        self.test_results: Dict[str, TestResult] = {}
        self.previously_passing: Set[str] = set()

    def _get_default_prompt(self) -> str:
        """Get default prompt template if prompt-fix.md doesn't exist."""
        return PROMPT_FIX

    def discover_and_run_tests(self) -> Tuple[int, int]:
        """
        Discover and run all tests, updating internal state.

        Returns:
            Tuple of (passing_count, failing_count)
        """
        print("\n" + "=" * 80)
        print("🔍 DISCOVERING AND RUNNING TESTS")
        print("=" * 80)

        if self.verbose:
            print(f"🔧 Test paths: {self.test_paths}")
            print(f"🔧 Verbose mode: {self.verbose}")
            print(f"🔧 Debug mode: {self.debug}")

        self.test_results = self.test_runner.run_full_test_suite(
            self.test_paths, verbose=self.verbose
        )

        # Update previously passing set
        self.previously_passing = {
            name
            for name, result in self.test_results.items()
            if result.status == "PASSING"
        }

        passing_count = len(self.previously_passing)
        failing_count = len([
            r for r in self.test_results.values() if r.status == "FAILING"
        ])
        skipped_count = len([
            r for r in self.test_results.values() if r.status == "SKIPPED"
        ])

        print(f"📊 Test Results:")
        print(f"   ✅ Passing: {passing_count}")
        print(f"   ❌ Failing: {failing_count}")
        if skipped_count > 0:
            print(f"   ⏭️ Skipped: {skipped_count}")
        print(f"   📋 Total: {len(self.test_results)}")

        if self.verbose and failing_count > 0:
            print(f"\n📝 First few failing tests:")
            failing_tests = [
                name
                for name, result in self.test_results.items()
                if result.status == "FAILING"
            ]
            for i, test_name in enumerate(failing_tests[:5], 1):
                print(f"   {i}. {test_name}")
            if len(failing_tests) > 5:
                print(f"   ... and {len(failing_tests) - 5} more")

        return passing_count, failing_count

    def get_random_failing_test(self) -> Optional[str]:
        """Get a random failing test name."""
        failing_tests = [
            name
            for name, result in self.test_results.items()
            if result.status == "FAILING"
        ]

        if not failing_tests:
            return None

        return random.choice(failing_tests)

    def run_claude_on_test(self, test_name: str) -> bool:
        """
        Run Claude Code on a specific test.

        Args:
            test_name: Name of the test to fix

        Returns:
            True if Claude ran successfully, False otherwise
        """
        print(f"\n🤖 Running Claude Code on test: {test_name}")

        # Get test output for context
        test_result = self.test_results.get(test_name)
        test_output = (
            test_result.output if test_result else "No previous output available"
        )

        # Format the prompt
        prompt = self.prompt_template.format(
            test_name=test_name, test_output=test_output
        )

        if self.debug:
            print(f"\n🔍 DEBUG: Prompt being sent to Claude:")
            print(f"{'=' * 60}")
            print(prompt)
            print(f"{'=' * 60}\n")

        try:
            cmd = ["claude", "--dangerously-skip-permissions", "-p", prompt]

            if self.verbose:
                print(f"🔧 Running command: {' '.join(cmd[:3])} [prompt...]")

            result = subprocess.run(
                cmd,
                text=True,
                capture_output=False,  # Let Claude output be visible
            )

            success = result.returncode == 0
            print(
                f"{'✅' if success else '❌'} Claude finished with return code: {result.returncode}"
            )
            return success

        except subprocess.CalledProcessError as e:
            print(f"❌ Error running Claude: {e}")
            return False
        except KeyboardInterrupt:
            print(f"\n⚠️ Claude interrupted by user")
            return False

    def check_test_fixed(self, test_name: str) -> bool:
        """
        Check if a test is now passing.

        Args:
            test_name: Name of the test to check

        Returns:
            True if test is now passing, False otherwise
        """
        print(f"🎯 Checking if test is fixed: {test_name}")

        result = self.test_runner.run_single_test(test_name)

        if self.verbose:
            print(f"🔧 Test check result: {result.status}")
            if result.output and self.debug:
                print(f"🔍 Test output: {result.output[:200]}...")

        if result.status == "PASSING":
            print(f"✅ Test {test_name} is now PASSING!")
            return True
        else:
            print(f"❌ Test {test_name} is still FAILING")
            sys.exit(1)
            return False

    def check_no_regression(self) -> bool:
        """
        Check that all previously passing tests are still passing.

        Returns:
            True if no regression detected, False otherwise
        """
        print(
            f"🛡️ Checking for regressions in {len(self.previously_passing)} previously passing tests..."
        )

        if self.verbose:
            print(
                f"🔧 Running regression check on {len(self.previously_passing)} tests"
            )

        failed_tests = []

        for i, test_name in enumerate(self.previously_passing, 1):
            if self.verbose and i <= 3:  # Show progress for first few
                print(f"   🔍 Checking {test_name}...")
            elif self.verbose and i == 4 and len(self.previously_passing) > 3:
                print(
                    f"   🔍 Checking remaining {len(self.previously_passing) - 3} tests..."
                )

            result = self.test_runner.run_single_test(test_name)
            if result.status == "FAILING":
                failed_tests.append(test_name)

        if failed_tests:
            print(
                f"❌ Regression detected! {len(failed_tests)} previously passing tests now failing:"
            )
            for test in failed_tests[:5]:  # Show first 5
                print(f"   - {test}")
            if len(failed_tests) > 5:
                print(f"   ... and {len(failed_tests) - 5} more")
            return False
        else:
            print(
                f"✅ No regression detected - all previously passing tests still pass"
            )
            return True

    def fix_single_test(self, test_name: str) -> bool:
        """
        Attempt to fix a single test.

        Args:
            test_name: Name of the test to fix

        Returns:
            True if test was successfully fixed, False otherwise
        """
        print(f"\n{'=' * 80}")
        print(f"🔧 ATTEMPTING TO FIX TEST: {test_name}")
        print(f"{'=' * 80}")

        # Record initial state
        initial_commit = self.git_manager.get_current_commit()

        # Step 1: Run Claude
        if not self.run_claude_on_test(test_name):
            print(f"❌ Claude failed for test {test_name}")
            return False

        # Step 2: Check if Claude made any changes
        if not self.git_manager.has_uncommitted_changes():
            print(f"⚠️ No changes detected after Claude run for {test_name}")
            return False

        # Step 3: Check if test is now fixed
        if not self.check_test_fixed(test_name):
            print(f"❌ Test {test_name} not fixed - rolling back changes")
            self.git_manager.reset_to_commit(initial_commit)
            return False

        # Step 4: Check for regressions
        if not self.check_no_regression():
            print(f"❌ Regression detected for {test_name} - rolling back changes")
            self.git_manager.reset_to_commit(initial_commit)
            return False

        # Step 5: Commit successful fix
        commit_message = (
            f"fix: resolve failing test {test_name}\n\n🤖 Generated with ClaudeBot"
        )
        if self.git_manager.commit_changes(commit_message):
            print(f"✅ Successfully fixed and committed {test_name}")

            # Update our test state
            if test_name in self.test_results:
                self.test_results[test_name].status = "PASSING"
            self.previously_passing.add(test_name)

            return True
        else:
            print(f"❌ Failed to commit changes for {test_name}")
            self.git_manager.reset_to_commit(initial_commit)
            return False

    def run_continuous_fixing(
        self, max_iterations: Optional[int] = None, delay_between_tests: int = 60
    ) -> None:
        """
        Run the continuous test fixing loop.

        Args:
            max_iterations: Maximum number of fix attempts (None for unlimited)
            delay_between_tests: Delay in seconds between test fix attempts
        """
        print("🚀 Starting ClaudeBot - Autonomous Test Fixing")
        print(f"📝 Using prompt template: {self.prompt_file}")
        print(f"⏰ Delay between tests: {delay_between_tests} seconds")
        if max_iterations:
            print(f"🔄 Max iterations: {max_iterations}")
        else:
            print(f"🔄 Running indefinitely (Ctrl+C to stop)")

        # Initial test discovery
        passing, failing = self.discover_and_run_tests()

        if failing == 0:
            print("🎉 All tests are already passing! Nothing to fix.")
            return

        iteration = 0
        fixes_made = 0

        try:
            while True:
                iteration += 1

                if max_iterations and iteration > max_iterations:
                    print(f"\n🏁 Reached maximum iterations ({max_iterations})")
                    break

                # Get a random failing test
                test_to_fix = self.get_random_failing_test()

                if not test_to_fix:
                    print("\n🎉 No more failing tests! All tests are now passing.")
                    break

                print(f"\n{'=' * 80}")
                print(f"🔄 ITERATION {iteration}")
                print(f"🎯 Selected test to fix: {test_to_fix}")
                print(f"{'=' * 80}")

                # Attempt to fix the test
                if self.fix_single_test(test_to_fix):
                    fixes_made += 1
                    print(f"🎊 Fix #{fixes_made} completed successfully!")
                else:
                    print(f"💔 Fix attempt failed for {test_to_fix}")

                # Status update
                current_failing = len([
                    r for r in self.test_results.values() if r.status == "FAILING"
                ])
                print(f"\n📊 Current status:")
                print(f"   🔧 Fixes made this session: {fixes_made}")
                print(f"   ❌ Tests still failing: {current_failing}")
                print(f"   ✅ Tests passing: {len(self.previously_passing)}")

                # Delay before next iteration (unless this is the last one)
                if max_iterations is None or iteration < max_iterations:
                    if current_failing > 0:
                        print(
                            f"\n⏳ Waiting {delay_between_tests} seconds before next test..."
                        )
                        print("   (Press Ctrl+C to stop)")
                        time.sleep(delay_between_tests)

        except KeyboardInterrupt:
            print(f"\n🛑 ClaudeBot stopped by user")

        # Final summary
        self.print_final_summary(fixes_made, iteration)

    def print_final_summary(self, fixes_made: int, iterations: int) -> None:
        """Print final summary of the ClaudeBot session."""
        print(f"\n{'=' * 80}")
        print(f"📊 CLAUDEBOT SESSION SUMMARY")
        print(f"{'=' * 80}")
        print(f"🔄 Iterations completed: {iterations}")
        print(f"🔧 Tests fixed: {fixes_made}")

        current_failing = len([
            r for r in self.test_results.values() if r.status == "FAILING"
        ])
        current_passing = len(self.previously_passing)
        total = current_passing + current_failing

        if total > 0:
            success_rate = (current_passing / total) * 100
            print(f"✅ Tests currently passing: {current_passing}")
            print(f"❌ Tests still failing: {current_failing}")
            print(f"📊 Success rate: {success_rate:.1f}%")

            if fixes_made > 0:
                print(f"\n🎉 ClaudeBot successfully improved the test suite!")
            elif current_failing == 0:
                print(f"\n🏆 All tests are now passing!")
            else:
                print(f"\n💪 Keep running ClaudeBot to fix more tests!")

#
# Utils
#
def convert_test_name_to_pytest_path(test_name: str) -> str:
    # Split on '::' to separate module/class from test function
    parts = test_name.split("::")
    if not parts or len(parts) < 2:
        return test_name  # fallback

    # Replace dots with slashes in the module path, add .py extension
    module_path = parts[0].replace(".", "/") + ".py"
    rest = "::".join(parts[1:])

    return f"{module_path}::{rest}"


assert convert_test_name_to_pytest_path("tests.test_example::test_method") \
    == "tests/test_example.py::test_method"

if __name__ == "__main__":
    main()
