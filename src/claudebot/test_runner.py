"""Test execution and result parsing for ClaudeBot."""

import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

from .models import TestResult
from .utils import convert_test_name_to_pytest_path


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