"""Prompt generator interface and base classes for ClaudeBot."""

from abc import ABC, abstractmethod
from typing import Iterator, Dict, Any, Optional
from .models import TestResult


class PromptRequest:
    """Represents a request for Claude to work on."""

    def __init__(
        self, prompt: str, description: str, context: Optional[Dict[str, Any]] = None
    ):
        self.prompt = prompt
        self.description = description
        self.context = context or {}


class PromptGenerator(ABC):
    """Abstract base class for prompt generators."""

    @abstractmethod
    def get_prompts(
        self, test_results: Dict[str, TestResult], **kwargs
    ) -> Iterator[PromptRequest]:
        """
        Generate prompts for Claude to work on.

        Args:
            test_results: Current test results from the test suite
            **kwargs: Additional context (verbose, debug, etc.)

        Yields:
            PromptRequest objects containing prompts and metadata
        """
        pass

    @abstractmethod
    def should_continue(self, test_results: Dict[str, TestResult]) -> bool:
        """
        Determine if the generator should continue producing prompts.

        Args:
            test_results: Current test results

        Returns:
            True if more prompts should be generated, False to stop
        """
        pass

    def on_prompt_completed(
        self, request: PromptRequest, success: bool, test_results: Dict[str, TestResult]
    ) -> None:
        """
        Called after a prompt has been processed.

        Args:
            request: The completed prompt request
            success: Whether the prompt execution was successful
            test_results: Updated test results after prompt execution
        """
        pass


class FunctionBasedGenerator(PromptGenerator):
    """Wrapper for function-based prompt generators."""

    def __init__(self, get_prompts_func):
        self.get_prompts_func = get_prompts_func

    def get_prompts(
        self, test_results: Dict[str, TestResult], **kwargs
    ) -> Iterator[PromptRequest]:
        """Delegate to the wrapped function."""
        yield from self.get_prompts_func(test_results, **kwargs)

    def should_continue(self, test_results: Dict[str, TestResult]) -> bool:
        """For function-based generators, always continue (let the function decide)."""
        return True
