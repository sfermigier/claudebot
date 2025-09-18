"""Data models for ClaudeBot."""

from dataclasses import dataclass


@dataclass
class TestResult:
    """Represents the result of a single test."""

    name: str
    status: str  # "PASSING", "FAILING", or "SKIPPED"
    output: str = ""