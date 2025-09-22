#!/usr/bin/env python3
"""
Example implementation comparator generator.
"""

from pathlib import Path

PROMPT_TEMPLATE = """
We are working on rewriting a project from C to Python.

I need you to compare and synchronize two implementations of the same module.

Module: {module_name}

Python implementation: {py_file}
C implementation: {c_file}

Please:
1. Analyze both implementations for functional equivalence
2. Identify any differences in behavior or logic
3. If needed, suggest improvements to make the Python version more equivalent to the C version
4. If needed, fix any bugs or inconsistencies in the Python version

Focus on ensuring the Python implementation produces the same results for the same inputs as the C implementation. Note that the Python version should be idiomatic and leverage Python's strengths, but must remain strictly functionally equivalent to the C version.
"""


def get_prompts():
    """Generate prompts to compare implementations."""
    python_dir = Path("src/qbe")
    c_dir = Path("qbe-c-orig/qbe")

    if not python_dir.exists() or not c_dir.exists():
        print(f"⚠️ Directories not found: {python_dir} or {c_dir}")
        return

    # Find C files and try to match with Python files
    for c_file in c_dir.rglob("*.c"):
        # Get relative path from c_dir to preserve directory structure
        relative_path = c_file.relative_to(c_dir)
        module_name = c_file.stem

        # Look for corresponding Python file with same relative path
        py_file = python_dir / relative_path.with_suffix(".py")

        prompt = PROMPT_TEMPLATE.format(
            module_name=module_name,
            py_file=py_file,
            c_file=c_file
        )

        yield {
            "prompt": prompt,
            "description": f"Compare {module_name}: Python vs C",
        }
