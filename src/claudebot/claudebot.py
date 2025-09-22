"""Main ClaudeBot class and CLI functionality."""

import importlib.util
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import default_prompt_generator

DEFAULT_PROMPT_MODULE = "claudebot.default_prompt_generator"


@dataclass
class ClaudeBot:
    """Main ClaudeBot class for autonomous task execution."""

    prompt_generator_module: str = ""
    verbose: bool = False
    debug: bool = False

    # Keep main method at the top for to make the structure clear
    def run_continuous_loop(self, delay_between_iterations: int = 60) -> None:
        """
        Run the task execution loop until generator is exhausted.

        Args:
            delay_between_iterations: Delay in seconds between iterations
        """
        generator_func = self._get_generator_function()
        generator_name = self.prompt_generator_module or "default generator"

        print("🚀 Starting ClaudeBot")
        print(f"🎯 Using prompt generator: {generator_name}")
        print(f"⏰ Delay between iterations: {delay_between_iterations} seconds")

        iteration = 0
        tasks_completed = 0

        try:
            current_generator = generator_func()

            while True:
                iteration += 1

                print(f"\n{'=' * 80}")
                print(f"🔄 ITERATION {iteration}")
                print(f"{'=' * 80}")

                # Get next prompt from generator
                try:
                    prompt_dict = next(current_generator)
                except StopIteration:
                    print("🏁 Generator exhausted, stopping...")
                    break
                except Exception as e:
                    print(f"❌ Error in prompt generator: {e}")
                    break

                description = prompt_dict.get("description", "Unknown task")
                print(f"🎯 Processing: {description}")

                # Execute the prompt
                success = self._execute_prompt(prompt_dict)

                if success:
                    tasks_completed += 1
                    print(f"🎊 Task #{tasks_completed} completed successfully!")
                else:
                    print("💔 Task failed")

                print(f"\n📊 Tasks completed this session: {tasks_completed}")

                # Delay before next iteration
                print(f"\n⏳ Waiting {delay_between_iterations} seconds before next iteration...")
                print("   (Press Ctrl+C to stop)")
                time.sleep(delay_between_iterations)

        except KeyboardInterrupt:
            print("\n🛑 ClaudeBot stopped by user")
        except Exception as e:
            print(f"\n💀 FATAL: ClaudeBot stopped due to error: {e}")
            sys.exit(1)

        # Final summary
        print(f"\n{'=' * 80}")
        print("📊 CLAUDEBOT SESSION SUMMARY")
        print(f"{'=' * 80}")
        print(f"🔄 Iterations completed: {iteration}")
        print(f"🔧 Tasks completed: {tasks_completed}")

        if tasks_completed > 0:
            print("\n🎉 ClaudeBot successfully completed tasks!")
        else:
            print("\n💪 Keep running ClaudeBot to complete more tasks!")

    def _get_generator_function(self) -> Callable:
        """Load generator function from module or use default."""
        if not self.prompt_generator_module:
            return default_prompt_generator.get_prompts

        generator_path = self.prompt_generator_module

        try:
            # Handle .py file paths
            if generator_path.endswith(".py"):
                module_path = Path(generator_path)
                if not module_path.exists():
                    raise ImportError(f"Module file not found: {module_path}")

                spec = importlib.util.spec_from_file_location(
                    "prompt_generator", module_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                # Handle module import paths (e.g., package.module)
                module = importlib.import_module(generator_path)

            # Look for get_prompts function
            if hasattr(module, "get_prompts"):
                return module.get_prompts

            raise ImportError(
                f"No get_prompts function found in module: {generator_path}"
            )

        except Exception as e:
            print(f"❌ Failed to load prompt generator from {generator_path}: {e}")
            raise

    def _execute_prompt(self, prompt_dict: dict) -> bool:
        """Execute a prompt using Claude."""
        prompt = prompt_dict["prompt"]
        description = prompt_dict.get("description", "Unknown task")

        print(f"\n🤖 Running Claude Code: {description}")

        if self.debug:
            print("\n🔍 DEBUG: Prompt being sent to Claude:")
            print(f"{'=' * 60}")
            print(prompt)
            print(f"{'=' * 60}\n")

        try:
            cmd = [
                "claude",
                "--dangerously-skip-permissions",
                "-c",
                "-p",
                prompt,
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
