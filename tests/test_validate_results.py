import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VALID_REPORT = {"exit_code": 0, "phases": [{"index": 0}]}
VALIDATOR = Path(__file__).resolve().parents[1] / "validate_results.py"


class ValidateResultsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write_pair(self, version, iteration):
        pair = self.root / version / f"iter_{iteration}"
        pair.mkdir(parents=True)
        for build in ("cold", "warm"):
            (pair / f"{build}_build.json").write_text(
                json.dumps(VALID_REPORT), encoding="utf-8"
            )
        return pair

    def run_validator(self):
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(self.root)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_complete_successful_pair(self):
        self.write_pair("2.14.0", 0)
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Valid cold/warm pairs: 1", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_failed_maven_missing_and_invalid_reports_are_reported_together(self):
        failed = self.write_pair("2.14.0", 0)
        (failed / "cold_build.json").write_text(
            json.dumps({**VALID_REPORT, "exit_code": 42}), encoding="utf-8"
        )
        missing = self.write_pair("2.14.0", 1)
        (missing / "warm_build.json").unlink()
        invalid = self.write_pair("2.14.0", 2)
        (invalid / "warm_build.json").write_text("{", encoding="utf-8")
        self.write_pair("2.14.0", 3)

        result = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("2.14.0/iter_0/cold_build.json: Maven exited with status 42", result.stderr)
        self.assertIn("2.14.0/iter_1/warm_build.json: report is missing", result.stderr)
        self.assertIn("2.14.0/iter_2/warm_build.json: report is not valid UTF-8 JSON", result.stderr)
        self.assertIn("Valid cold/warm pairs: 1", result.stdout)

    def test_empty_results_are_rejected(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("no benchmark iterations found", result.stderr)

    def test_missing_exit_code_and_empty_phases_are_rejected(self):
        pair = self.write_pair("2.14.0", 0)
        (pair / "cold_build.json").write_text('{"phases": [{}]}', encoding="utf-8")
        (pair / "warm_build.json").write_text('{"exit_code": 0, "phases": []}', encoding="utf-8")

        result = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("cold_build.json: expected an integer Maven exit_code", result.stderr)
        self.assertIn("warm_build.json: expected a non-empty phases list", result.stderr)
