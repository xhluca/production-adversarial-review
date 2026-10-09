#!/usr/bin/env python3
"""Strict evidence comparison. Does not execute a PR or approve a merge.

Usage: python compare_observations.py baseline.json candidate.json
Exit 0 = strict healthy equality; 1 = differences/unhealthy; 2 = invalid input.
See EVIDENCE.md for the schema and the limits of this helper.
"""
import argparse
import json
import sys
from pathlib import Path


class EvidenceError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def invalid_constant(value):
    raise EvidenceError("Non-finite JSON number: " + value)


def load_document(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"),
                          object_pairs_hook=unique_object,
                          parse_constant=invalid_constant)
    except (OSError, UnicodeError, ValueError) as error:
        raise EvidenceError(str(error)) from error


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def string_list(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def index_document(document):
    require(isinstance(document, dict), "Document must be an object")
    require(type(document.get("schema_version")) is int and document["schema_version"] == 1,
            "schema_version must be 1")
    require(isinstance(document.get("revision"), str) and bool(document["revision"].strip()),
            "Missing pinned revision label")
    require(isinstance(document.get("environment"), dict) and bool(document["environment"]),
            "environment must be a nonempty object")
    planned = document.get("case_ids")
    require(string_list(planned) and bool(planned) and all(item.strip() for item in planned),
            "case_ids must be a nonempty list of nonempty strings")
    require(len(set(planned)) == len(planned), "Duplicate planned case IDs")
    records = document.get("observations")
    require(isinstance(records, list), "observations must be a list")
    indexed = {}
    for record in records:
        require(isinstance(record, dict), "Observation must be an object")
        case_id = record.get("id")
        require(isinstance(case_id, str) and bool(case_id.strip()), "Invalid observation ID")
        require(case_id not in indexed, "Duplicate observation ID: " + case_id)
        require(record.get("status") in ("ok", "error", "crash", "timeout", "skipped"),
                "Invalid status: " + case_id)
        require(record.get("expect") in ("ok", "error"), "Missing expectation: " + case_id)
        require(string_list(record.get("warnings")), "warnings must be a string list: " + case_id)
        if "expected_warnings" in record:
            require(string_list(record["expected_warnings"]), "Invalid expected_warnings: " + case_id)
        checks = record.get("checks", {})
        require(isinstance(checks, dict) and all(isinstance(k, str) and k.strip() and type(v) is bool for k, v in checks.items()),
                "checks must map names to booleans: " + case_id)
        if record["status"] == "ok":
            require("value" in record, "Missing successful value: " + case_id)
            require(bool(checks), "Successful record needs an independent contract check: " + case_id)
        if record["expect"] == "error":
            expected = record.get("expected_error")
            require(isinstance(expected, dict) and isinstance(expected.get("type"), str) and bool(expected["type"]),
                    "Expected error needs a type: " + case_id)
            require(any(isinstance(expected.get(key), str) and bool(expected[key]) for key in ("code", "message")),
                    "Expected error needs an exact code or message: " + case_id)
            require(set(expected).issubset({"type", "code", "message"}), "Unsupported error expectation: " + case_id)
            require(all(isinstance(value, str) and bool(value) for value in expected.values()),
                    "Expected error fields must be nonempty strings: " + case_id)
        if record["status"] == "error":
            error = record.get("error")
            require(isinstance(error, dict) and isinstance(error.get("type"), str) and bool(error["type"]),
                    "Error record needs a type: " + case_id)
            require(any(isinstance(error.get(key), str) and bool(error[key]) for key in ("code", "message")),
                    "Error record needs a diagnostic: " + case_id)
        indexed[case_id] = record
    require(set(indexed) == set(planned), "Observed cases do not exactly match the planned case IDs")
    try:
        canonical(document)
    except (TypeError, ValueError) as error:
        raise EvidenceError("Non-JSON or non-finite evidence") from error
    return indexed


def unhealthy(record):
    problems = []
    status = record["status"]
    if status in ("crash", "timeout", "skipped"):
        problems.append(status)
    elif status != record["expect"]:
        problems.append("unexpected " + status)
    elif status == "error":
        if any(record["error"].get(key) != expected for key, expected in record["expected_error"].items()):
            problems.append("wrong error contract")
    problems.extend("failed check: " + name for name, passed in record.get("checks", {}).items() if not passed)
    if record["warnings"] != record.get("expected_warnings", []):
        problems.append("unexpected warnings")
    return problems


def compare_documents(baseline, candidate):
    old = index_document(baseline)
    new = index_document(candidate)
    require(set(old) == set(new), "Baseline and candidate have different planned case sets")
    issues = []
    if canonical(baseline["environment"]) != canonical(candidate["environment"]):
        issues.append({"case": None, "kind": "environment mismatch"})
    healthy_pairs = 0
    matching_pairs = 0
    for case_id in sorted(old):
        a, b = old[case_id], new[case_id]
        a_problems, b_problems = unhealthy(a), unhealthy(b)
        if not a_problems and not b_problems:
            healthy_pairs += 1
        for side, problems in (("baseline", a_problems), ("candidate", b_problems)):
            for problem in problems:
                issues.append({"case": case_id, "side": side, "kind": problem})
        expectation_a = {key: a.get(key) for key in ("expect", "expected_error", "expected_warnings")}
        expectation_b = {key: b.get(key) for key in ("expect", "expected_error", "expected_warnings")}
        if canonical(expectation_a) != canonical(expectation_b):
            issues.append({"case": case_id, "kind": "expectation drift"})
        if canonical(a) == canonical(b):
            matching_pairs += 1
        else:
            issues.append({"case": case_id, "kind": "record mismatch"})
    return {
        "baseline_revision": baseline["revision"],
        "candidate_revision": candidate["revision"],
        "planned_pairs": len(old),
        "healthy_pairs": healthy_pairs,
        "strictly_matching_pairs": matching_pairs,
        "issue_count": len(issues),
        "issues": issues[:20],
        "issues_truncated": len(issues) > 20,
        "strict_comparison_passed": not issues,
        "merge_approval": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    args = parser.parse_args(argv)
    try:
        report = compare_documents(load_document(args.baseline), load_document(args.candidate))
    except EvidenceError as error:
        print(json.dumps({"invalid_evidence": str(error), "merge_approval": False}), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["strict_comparison_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
