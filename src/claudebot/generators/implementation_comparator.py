"""Implementation comparator prompt generator for comparing two codebases."""

from pathlib import Path
from typing import Dict, List, Tuple
from collections.abc import Iterator
from ..prompt_generator import PromptGenerator, PromptRequest
from ..models import TestResult

DEFAULT_COMPARISON_TEMPLATE = """
I need you to compare two implementations of the same functionality and ensure they are equivalent.

Module to compare: {module_name}

Implementation 1 ({impl1_lang}):
{impl1_path}

Implementation 2 ({impl2_lang}):
{impl2_path}

Please:

1. Analyze both implementations to understand their functionality
2. Identify any differences in behavior, logic, or edge cases
3. Suggest improvements to make them more equivalent
4. Fix any bugs or inconsistencies you find
5. Ensure both implementations handle the same inputs and produce the same outputs

Focus on:
- Algorithmic equivalence
- Error handling
- Edge cases
- Performance considerations
- Code style and maintainability

Please examine and improve both implementations now.
"""


class ImplementationComparatorGenerator(PromptGenerator):
    """Generates prompts to compare and synchronize two implementations."""

    def __init__(
        self,
        impl1_dir: str = "src",
        impl2_dir: str = "reference",
        impl1_lang: str = "Python",
        impl2_lang: str = "C",
        file_patterns: List[str] = None,
        prompt_template: str = DEFAULT_COMPARISON_TEMPLATE,
    ):
        self.impl1_dir = Path(impl1_dir)
        self.impl2_dir = Path(impl2_dir)
        self.impl1_lang = impl1_lang
        self.impl2_lang = impl2_lang
        self.file_patterns = file_patterns or ["*.py", "*.c", "*.h", "*.cpp", "*.hpp"]
        self.prompt_template = prompt_template.strip()
        self._processed_modules = set()

    def _find_comparable_files(self) -> List[Tuple[Path, Path]]:
        """Find pairs of files that should be compared."""
        pairs = []

        if not self.impl1_dir.exists() or not self.impl2_dir.exists():
            return pairs

        # Find files in impl1 and try to match them in impl2
        for pattern in self.file_patterns:
            for impl1_file in self.impl1_dir.rglob(pattern):
                # Try to find corresponding file in impl2
                relative_path = impl1_file.relative_to(self.impl1_dir)

                # Try exact match first
                impl2_file = self.impl2_dir / relative_path
                if impl2_file.exists():
                    pairs.append((impl1_file, impl2_file))
                    continue

                # Try with different extensions
                stem = relative_path.stem
                for ext_pattern in self.file_patterns:
                    ext = ext_pattern.replace("*", "")
                    potential_file = (
                        self.impl2_dir / relative_path.parent / f"{stem}{ext}"
                    )
                    if potential_file.exists():
                        pairs.append((impl1_file, potential_file))
                        break

        return pairs

    def get_prompts(
        self, test_results: Dict[str, TestResult], **kwargs
    ) -> Iterator[PromptRequest]:
        """Generate prompts for comparing implementations."""
        file_pairs = self._find_comparable_files()

        for impl1_file, impl2_file in file_pairs:
            module_name = impl1_file.stem

            # Skip if already processed this module
            if module_name in self._processed_modules:
                continue

            self._processed_modules.add(module_name)

            prompt = self.prompt_template.format(
                module_name=module_name,
                impl1_lang=self.impl1_lang,
                impl1_path=str(impl1_file),
                impl2_lang=self.impl2_lang,
                impl2_path=str(impl2_file),
            )

            yield PromptRequest(
                prompt=prompt,
                description=f"Compare implementations: {module_name} ({self.impl1_lang} vs {self.impl2_lang})",
                context={
                    "module_name": module_name,
                    "impl1_file": str(impl1_file),
                    "impl2_file": str(impl2_file),
                    "impl1_lang": self.impl1_lang,
                    "impl2_lang": self.impl2_lang,
                    "generator_type": "implementation_comparator",
                },
            )

    def should_continue(self, test_results: Dict[str, TestResult]) -> bool:
        """Continue until all modules have been compared."""
        file_pairs = self._find_comparable_files()
        unprocessed_modules = {
            pair[0].stem
            for pair in file_pairs
            if pair[0].stem not in self._processed_modules
        }
        return len(unprocessed_modules) > 0

    def on_prompt_completed(
        self, request: PromptRequest, success: bool, test_results: Dict[str, TestResult]
    ) -> None:
        """Handle completion of an implementation comparison."""
        module_name = request.context.get("module_name")
        if success and module_name:
            print(f"🔄 Successfully compared implementations: {module_name}")
        elif module_name:
            print(f"💔 Failed to compare implementations: {module_name}")


def get_prompts(
    test_results: Dict[str, TestResult], **kwargs
) -> Iterator[PromptRequest]:
    """Entry point function for module-based loading."""
    # Extract configuration from kwargs
    impl1_dir = kwargs.get("impl1_dir", "src")
    impl2_dir = kwargs.get("impl2_dir", "reference")
    impl1_lang = kwargs.get("impl1_lang", "Python")
    impl2_lang = kwargs.get("impl2_lang", "C")

    generator = ImplementationComparatorGenerator(
        impl1_dir=impl1_dir,
        impl2_dir=impl2_dir,
        impl1_lang=impl1_lang,
        impl2_lang=impl2_lang,
    )
    yield from generator.get_prompts(test_results, **kwargs)
