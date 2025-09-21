"""Main ClaudeBot class and CLI functionality."""

import importlib.util
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from .git_manager import GitManager, GitError
from .models import TestResult
from .test_runner import TestRunner
from .prompt_generator import PromptGenerator, PromptRequest, FunctionBasedGenerator
from .generators.test_fixer import TestFixerGenerator

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


class ClaudeBot:
    """Main ClaudeBot class for autonomous test fixing."""

    def __init__(
        self,
        test_paths: list[str],
        prompt_file: str = "prompt-fix.md",
        prompt_generator_module: Optional[str] = None,
        verbose: bool = False,
        debug: bool = False,
    ):
        self.test_paths = test_paths
        self.prompt_file = Path(prompt_file)
        self.verbose = verbose
        self.debug = debug
        self.git_manager = GitManager()
        self.test_runner = TestRunner()

        # Load prompt generator
        self.prompt_generator = self._load_prompt_generator(
            prompt_generator_module, prompt_file
        )

        # Test state tracking
        self.test_results: dict[str, TestResult] = {}
        self.previously_passing: set[str] = set()

    def _load_prompt_generator(
        self, generator_module: Optional[str], prompt_file: str
    ) -> PromptGenerator:
        """Load a prompt generator from module or use default test fixer."""
        if generator_module:
            return self._load_generator_from_module(generator_module)

        # Use default test fixer with custom prompt if available
        if self.prompt_file.exists():
            prompt_template = self.prompt_file.read_text()
            return TestFixerGenerator(prompt_template)
        print(
            f"⚠️ Warning: Prompt file {prompt_file} not found, using default prompt"
        )
        return TestFixerGenerator()

    def _load_generator_from_module(self, module_path: str) -> PromptGenerator:
        """Load prompt generator from a Python module."""
        try:
            # Handle .py file paths
            if module_path.endswith(".py"):
                module_path = Path(module_path)
                if not module_path.exists():
                    raise ImportError(f"Module file not found: {module_path}")

                spec = importlib.util.spec_from_file_location(
                    "prompt_generator", module_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                # Handle module import paths (e.g., package.module)
                module = importlib.import_module(module_path)

            # Look for get_prompts function
            if hasattr(module, "get_prompts"):
                # Create a wrapper generator for function-based generators
                return FunctionBasedGenerator(module.get_prompts)

            # Look for a class that implements PromptGenerator
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PromptGenerator)
                    and attr != PromptGenerator
                ):
                    return attr()

            raise ImportError(f"No prompt generator found in module: {module_path}")

        except Exception as e:
            print(f"❌ Failed to load prompt generator from {module_path}: {e}")
            print("🔄 Falling back to default test fixer generator")
            return TestFixerGenerator()

    def _execute_prompt_request(self, request: PromptRequest) -> bool:
        """Execute a prompt request using Claude."""
        print(f"\n🤖 Running Claude Code: {request.description}")

        if self.debug:
            print("\n🔍 DEBUG: Prompt being sent to Claude:")
            print(f"{'=' * 60}")
            print(request.prompt)
            print(f"{'=' * 60}\n")

        try:
            cmd = [
                "claude",
                "--dangerously-skip-permissions",
                "-c",
                "-p",
                request.prompt,
            ]

            if self.verbose:
                print(f"🔧 Running command: {' '.join(cmd[:4])} [prompt...]")

            # Stream Claude's output in real-time
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Stream output line by line
            for line in process.stdout:
                print(line, end="")

            # Wait for process to complete
            return_code = process.wait()

            success = return_code == 0
            print(
                f"\n{'✅' if success else '❌'} Claude finished with return code: {return_code}"
            )
            return success

        except subprocess.CalledProcessError as e:
            print(f"❌ Error running Claude: {e}")
            return False
        except KeyboardInterrupt:
            print("\n⚠️ Claude interrupted by user")
            if "process" in locals():
                process.terminate()
                process.wait()
            return False

    def _get_default_prompt(self) -> str:
        """Get default prompt template if prompt-fix.md doesn't exist."""
        return PROMPT_FIX

    def discover_and_run_tests(self) -> tuple[int, int]:
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

        print("📊 Test Results:")
        print(f"   ✅ Passing: {passing_count}")
        print(f"   ❌ Failing: {failing_count}")
        if skipped_count > 0:
            print(f"   ⏭️ Skipped: {skipped_count}")
        print(f"   📋 Total: {len(self.test_results)}")

        if self.verbose and failing_count > 0:
            print("\n📝 First few failing tests:")
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
            print("\n🔍 DEBUG: Prompt being sent to Claude:")
            print(f"{'=' * 60}")
            print(prompt)
            print(f"{'=' * 60}\n")

        try:
            cmd = ["claude", "--dangerously-skip-permissions", "-c", "-p", prompt]

            if self.verbose:
                print(f"🔧 Running command: {' '.join(cmd[:4])} [prompt...]")

            # Stream Claude's output in real-time
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Stream output line by line
            for line in process.stdout:
                print(line, end="")

            # Wait for process to complete
            return_code = process.wait()

            success = return_code == 0
            print(
                f"\n{'✅' if success else '❌'} Claude finished with return code: {return_code}"
            )
            return success

        except subprocess.CalledProcessError as e:
            print(f"❌ Error running Claude: {e}")
            return False
        except KeyboardInterrupt:
            print("\n⚠️ Claude interrupted by user")
            if "process" in locals():
                process.terminate()
                process.wait()
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
        print(f"❌ Test {test_name} is still FAILING")
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
        print("✅ No regression detected - all previously passing tests still pass")
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
        try:
            self.git_manager.commit_changes(commit_message)
            print(f"✅ Successfully fixed and committed {test_name}")

            # Update our test state
            if test_name in self.test_results:
                self.test_results[test_name].status = "PASSING"
            self.previously_passing.add(test_name)

            return True
        except GitError as e:
            print(f"❌ Failed to commit changes for {test_name}: {e}")
            print("❌ Rolling back changes...")
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
        print("🚀 Starting ClaudeBot")
        print(f"🎯 Using prompt generator: {type(self.prompt_generator).__name__}")
        print(f"⏰ Delay between iterations: {delay_between_tests} seconds")
        if max_iterations:
            print(f"🔄 Max iterations: {max_iterations}")
        else:
            print("🔄 Running indefinitely (Ctrl+C to stop)")

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

                # Check if generator wants to continue
                if not self.prompt_generator.should_continue(self.test_results):
                    print("\n🎉 Prompt generator indicates work is complete!")
                    print("🔄 Re-running test discovery to check for new work...")
                    passing, failing = self.discover_and_run_tests()

                    if not self.prompt_generator.should_continue(self.test_results):
                        print(
                            f"✅ No more work to do. Waiting {delay_between_tests} seconds before checking again..."
                        )
                        time.sleep(delay_between_tests)
                        continue

                print(f"\n{'=' * 80}")
                print(f"🔄 ITERATION {iteration}")
                print(f"{'=' * 80}")

                # Get prompts from generator
                prompts = list(
                    self.prompt_generator.get_prompts(
                        self.test_results, verbose=self.verbose, debug=self.debug
                    )
                )

                if not prompts:
                    print("⚠️ No prompts generated, checking again after delay...")
                    time.sleep(delay_between_tests)
                    continue

                # Process the first prompt (generators can yield multiple, but we process one per iteration)
                request = prompts[0]
                print(f"🎯 Processing: {request.description}")

                # Execute the prompt
                success = self._execute_prompt_request(request)

                # Notify generator of completion
                self.prompt_generator.on_prompt_completed(
                    request, success, self.test_results
                )

                if success:
                    fixes_made += 1
                    print(f"🎊 Task #{fixes_made} completed successfully!")
                else:
                    print(f"💔 Task failed: {request.description}")

                # Update test results after execution
                self.discover_and_run_tests()

                # Status update
                current_failing = len([
                    r for r in self.test_results.values() if r.status == "FAILING"
                ])
                print("\n📊 Current status:")
                print(f"   🔧 Tasks completed this session: {fixes_made}")
                print(f"   ❌ Tests failing: {current_failing}")
                print(f"   ✅ Tests passing: {len(self.previously_passing)}")

                # Delay before next iteration
                if max_iterations is None or iteration < max_iterations:
                    print(
                        f"\n⏳ Waiting {delay_between_tests} seconds before next iteration..."
                    )
                    print("   (Press Ctrl+C to stop)")
                    time.sleep(delay_between_tests)

        except KeyboardInterrupt:
            print("\n🛑 ClaudeBot stopped by user")
        except GitError as e:
            print(f"\n💀 FATAL: ClaudeBot stopped due to git error: {e}")
            print("💀 Please manually check and fix your repository state.")
            sys.exit(1)

        # Final summary
        self.print_final_summary(fixes_made, iteration)

    def print_final_summary(self, fixes_made: int, iterations: int) -> None:
        """Print final summary of the ClaudeBot session."""
        print(f"\n{'=' * 80}")
        print("📊 CLAUDEBOT SESSION SUMMARY")
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
                print("\n🎉 ClaudeBot successfully improved the test suite!")
            elif current_failing == 0:
                print("\n🏆 All tests are now passing!")
            else:
                print("\n💪 Keep running ClaudeBot to fix more tests!")


def main():
    """Main function with command line argument parsing."""
    import argparse
    from importlib.metadata import version

    try:
        pkg_version = version("claudebot")
    except Exception:
        pkg_version = "unknown"

    parser = argparse.ArgumentParser(
        description="ClaudeBot - Autonomous test fixing with Claude Code"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"claudebot {pkg_version}",
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
        "--prompt-generator",
        "--pg",
        type=str,
        default=None,
        help="Python module containing prompt generator (e.g., 'my_generator.py' or 'package.module')",
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
        args.test_paths,
        args.prompt,
        prompt_generator_module=args.prompt_generator,
        verbose=args.verbose,
        debug=args.debug,
    )

    if args.dry_run:
        print("🔍 DRY RUN MODE - Just discovering tests")
        bot.discover_and_run_tests()
        print("\n✅ Dry run complete")
    else:
        bot.run_continuous_fixing(
            max_iterations=args.max_iterations, delay_between_tests=args.delay
        )
