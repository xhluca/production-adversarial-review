"""Meaningful failure-mode tests for the strict evidence comparator."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from compare_observations import EvidenceError, compare_documents, load_document


def document():
    return {
        "schema_version": 1,
        "revision": "baseline-tree",
        "environment": {"runtime": "3.10", "backend": "numpy"},
        "case_ids": ["empty-index/query"],
        "observations": [{
            "id": "empty-index/query", "status": "ok", "expect": "ok",
            "value": {"dtype": "float32", "shape": [1, 0], "values": []},
            "checks": {"valid_shape": True}, "warnings": [],
        }],
    }


class ComparatorTests(unittest.TestCase):
    def test_healthy_equality_allows_different_revision(self):
        a = document()
        b = copy.deepcopy(a)
        b["revision"] = "candidate-tree"
        result = compare_documents(a, b)
        self.assertTrue(result["strict_comparison_passed"])
        self.assertFalse(result["merge_approval"])

    def test_equal_crashes_are_not_passes(self):
        a = document()
        a["observations"][0]["status"] = "crash"
        result = compare_documents(a, copy.deepcopy(a))
        self.assertFalse(result["strict_comparison_passed"])
        self.assertEqual(result["healthy_pairs"], 0)

    def test_equal_skips_and_timeouts_are_not_passes(self):
        for status in ("skipped", "timeout"):
            with self.subTest(status=status):
                a = document()
                a["observations"][0]["status"] = status
                self.assertFalse(compare_documents(a, a)["strict_comparison_passed"])

    def test_equal_unexpected_exceptions_are_not_passes(self):
        a = document()
        a["observations"][0].update(status="error", error={"type": "IndexError", "message": "out of bounds"})
        self.assertFalse(compare_documents(a, a)["strict_comparison_passed"])

    def test_expected_error_and_cleanup_pass(self):
        a = document()
        a["observations"][0].update(status="error", expect="error",
            error={"type": "ValueError", "code": "INVALID_K", "message": "k is negative"},
            expected_error={"type": "ValueError", "code": "INVALID_K"}, checks={"state_preserved": True})
        self.assertTrue(compare_documents(a, a)["strict_comparison_passed"])
        b = copy.deepcopy(a)
        b["observations"][0]["error"]["code"] = "MISSING_COLUMN"
        self.assertFalse(compare_documents(a, b)["strict_comparison_passed"])

    def test_type_only_expected_error_is_invalid(self):
        a = document()
        a["observations"][0].update(status="error", expect="error", error={"type": "ValueError", "message": "wrong"}, expected_error={"type": "ValueError"})
        with self.assertRaises(EvidenceError):
            compare_documents(a, a)

    def test_failed_contract_check_even_when_equal(self):
        a = document()
        a["observations"][0]["checks"]["valid_shape"] = False
        self.assertFalse(compare_documents(a, a)["strict_comparison_passed"])

    def test_missing_or_duplicate_records_are_invalid(self):
        for mode in ("missing", "duplicate", "unplanned"):
            with self.subTest(mode=mode):
                a = document()
                if mode == "missing":
                    a["observations"] = []
                elif mode == "duplicate":
                    a["observations"].append(copy.deepcopy(a["observations"][0]))
                else:
                    a["observations"][0]["id"] = "another-case"
                with self.assertRaises(EvidenceError):
                    compare_documents(a, a)

    def test_dtype_shape_and_value_changes_are_detected(self):
        for field, value in (("dtype", "object"), ("shape", [0]), ("values", [0])):
            with self.subTest(field=field):
                a, b = document(), document()
                b["observations"][0]["value"][field] = value
                self.assertFalse(compare_documents(a, b)["strict_comparison_passed"])

    def test_boolean_and_integer_are_not_equal_values(self):
        a, b = document(), document()
        a["observations"][0]["value"] = False
        b["observations"][0]["value"] = 0
        self.assertFalse(compare_documents(a, b)["strict_comparison_passed"])

    def test_unexpected_warning_and_expectation_drift_fail(self):
        a = document()
        a["observations"][0]["warnings"] = ["invalid division"]
        self.assertFalse(compare_documents(a, a)["strict_comparison_passed"])
        b = copy.deepcopy(a)
        b["observations"][0]["expected_warnings"] = ["invalid division"]
        self.assertFalse(compare_documents(a, b)["strict_comparison_passed"])

    def test_incompatible_environments_fail(self):
        a, b = document(), document()
        b["environment"]["backend"] = "numba"
        self.assertFalse(compare_documents(a, b)["strict_comparison_passed"])

    def test_nan_and_duplicate_json_fields_rejected(self):
        with tempfile.TemporaryDirectory() as path:
            file = Path(path) / "data.json"
            for text in ('{"value":NaN}', '{"value":1,"value":2}'):
                file.write_text(text)
                with self.assertRaises(EvidenceError):
                    load_document(file)

    def test_cli_exit_codes(self):
        script = Path(__file__).with_name("compare_observations.py")
        with tempfile.TemporaryDirectory() as path:
            base, candidate = Path(path) / "base.json", Path(path) / "candidate.json"
            base.write_text(json.dumps(document()))
            for expected_code in (0, 1, 2):
                b = document()
                if expected_code == 1:
                    b["observations"][0]["checks"]["valid_shape"] = False
                elif expected_code == 2:
                    b["observations"] = []
                candidate.write_text(json.dumps(b))
                result = subprocess.run([sys.executable, str(script), str(base), str(candidate)], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
