"""Unit tests for CLI functionality."""

import sys
from unittest.mock import patch

import pytest

from claudebot.cli import main


class StubClaudeBot:
    """Stub ClaudeBot class for testing CLI."""

    def __init__(self, prompt_generator_module=None, verbose=False, debug=False):
        self.prompt_generator_module = prompt_generator_module
        self.verbose = verbose
        self.debug = debug
        self.run_continuous_loop_called = False
        self.delay_between_iterations = None

    def run_continuous_loop(self, delay_between_iterations=60):
        """Record that the method was called with the given parameters."""
        self.run_continuous_loop_called = True
        self.delay_between_iterations = delay_between_iterations


def test_cli_default_args():
    """Test CLI with default arguments."""
    test_args = ["claudebot"]

    with patch.object(sys, "argv", test_args):
        stub_bot = StubClaudeBot()

        # Mock the bot creation to return our stub
        def mock_bot_class(*args, **kwargs):
            return stub_bot

        main(mock_bot_class)

        # Verify the bot was configured correctly
        assert stub_bot.prompt_generator_module is None
        assert stub_bot.verbose is False
        assert stub_bot.debug is False
        assert stub_bot.run_continuous_loop_called is True
        assert stub_bot.delay_between_iterations == 60


def test_cli_all_args():
    """Test CLI with all arguments specified."""
    test_args = [
        "claudebot",
        "--prompt-generator",
        "custom_generator.py",
        "--delay",
        "30",
        "--verbose",
        "--debug",
    ]

    with patch.object(sys, "argv", test_args):
        stub_bot = StubClaudeBot()

        def mock_bot_class(*args, **kwargs):
            # Verify the constructor was called with correct args
            assert kwargs["prompt_generator_module"] == "custom_generator.py"
            assert kwargs["verbose"] is True
            assert kwargs["debug"] is True
            return stub_bot

        main(mock_bot_class)

        # Verify run_continuous_loop was called with correct args
        assert stub_bot.run_continuous_loop_called is True
        assert stub_bot.delay_between_iterations == 30


def test_cli_short_args():
    """Test CLI with short argument forms."""
    test_args = [
        "claudebot",
        "--pg",
        "short_generator.py",
        "-v",
        "-d",
    ]

    with patch.object(sys, "argv", test_args):
        stub_bot = StubClaudeBot()

        def mock_bot_class(*args, **kwargs):
            assert kwargs["prompt_generator_module"] == "short_generator.py"
            assert kwargs["verbose"] is True
            assert kwargs["debug"] is True
            return stub_bot

        main(mock_bot_class)

        assert stub_bot.run_continuous_loop_called is True


def test_cli_version():
    """Test CLI version argument."""
    test_args = ["claudebot", "--version"]

    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main(StubClaudeBot)

        # Version argument causes SystemExit with code 0
        assert exc_info.value.code == 0


def test_cli_help():
    """Test CLI help argument."""
    test_args = ["claudebot", "--help"]

    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main(StubClaudeBot)

        # Help argument causes SystemExit with code 0
        assert exc_info.value.code == 0


def test_cli_partial_args():
    """Test CLI with partial arguments."""
    test_args = [
        "claudebot",
        "--verbose",
    ]

    with patch.object(sys, "argv", test_args):
        stub_bot = StubClaudeBot()

        def mock_bot_class(*args, **kwargs):
            assert kwargs["prompt_generator_module"] is None  # default
            assert kwargs["verbose"] is True
            assert kwargs["debug"] is False  # default
            return stub_bot

        main(mock_bot_class)

        assert stub_bot.run_continuous_loop_called is True
        assert stub_bot.delay_between_iterations == 60  # default
