"""Command line interface for ClaudeBot."""

import argparse
from importlib.metadata import version

from .claudebot import ClaudeBot


def main(bot_class=ClaudeBot):
    """Main function with command line argument parsing."""
    pkg_version = version("claudebot")

    parser = argparse.ArgumentParser(
        description="ClaudeBot - Autonomous task execution with Claude Code"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"claudebot {pkg_version}",
    )
    parser.add_argument(
        "--prompt-generator",
        "--pg",
        type=str,
        default=None,
        help="Python module containing prompt generator (e.g., 'my_generator.py' or 'package.module')",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=60,
        help="Delay between iterations in seconds (default: 60)",
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
    bot = bot_class(
        prompt_generator_module=args.prompt_generator,
        verbose=args.verbose,
        debug=args.debug,
    )

    bot.run_continuous_loop(delay_between_iterations=args.delay)
