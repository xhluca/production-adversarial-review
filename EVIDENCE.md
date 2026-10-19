# Evidence, comparison, and merge decisions

## What a passing comparison means

Differential agreement answers whether the recorded behaviors match for specific inputs and configurations. It does not establish correct behavior, adequate coverage, or zero production risk. Identical crashes, incorrect outputs, or skipped runs can agree. Test expected results and invariants independently.

Separate these evidence classes:

- Previously supported inputs: preserve the established contract unless the PR deliberately changes it.
- Reported bug: reproduce baseline failure and verify candidate behavior with an independent oracle.
- Newly accepted input: validate creation and all relevant downstream consumers; baseline rejection is not an oracle for success.
- Invalid input: verify intended rejection, diagnostics, timing, and cleanup.
- Persistence/concurrency/native/resource behavior: test the state transition or operational property directly, not only final output values.

Use the relevant deployed baseline in addition to current target when there is a material release-format or rolling-update contract. Label each comparison clearly.

## Build a trustworthy differential harness

1. Pin both trees and run the same reviewed harness with the same synthetic fixtures, seed, and dependency environment. Record actual module/source paths and backend configuration.
2. Define planned case IDs and expected outcomes in advance. Reusing the same fixtures is intentional; count configurations, cases, assertions, and raw observations separately.
3. Record successful values with types/shapes, warnings, structured expected errors, relevant mutation snapshots, and timing/resource measurements when needed.
4. Capture exceptions, signals, timeouts, and skipped cases explicitly. Unexpected errors remain failures even if both sides produce them.
5. Compare semantic payloads and diagnosed invariants. Keep raw artifacts and produce a small human-readable explanation of each difference.
6. Minimize unexpected differences and verify the harness before attributing them to the PR.

For numeric arrays, serialize dtype, shape, and deterministic logical values or bytes of the numeric elements. Object-array bytes contain addresses of Python objects and vary across processes even when values are identical: use recursively serialized `.tolist()` values. Distinguish dictionaries, tuples, strings, scalars, and typed arrays according to the API's observable contract. Preserve byte order and signed zero/NaN representation only when contractually meaningful; explicitly document any canonicalization.

Strict JSON cannot represent NaN/infinity. Encode them explicitly with a documented typed representation, or treat non-finiteness as an invariant failure. Do not let permissive JSON readers accidentally compare NaNs as equal or different. Reject duplicate JSON keys/case IDs and incomplete outputs. Do not compare raw memory addresses, randomized IDs, timestamps, or machine-local paths as functional values; normalize only known nondeterminism, with an explicit rationale and a test that a real behavior difference is still detected.

Choose numeric tolerances and allowed tie behavior before examining failures. Record approved intended changes as individual case-level deltas with expected candidate results; do not ignore whole categories or all exceptions. Rerun those cases with the corrected oracle as well as unchanged-contract cases.

Avoid misleading confidence statements: 70,000 observations are not 70,000 independent tests, and passing seeded random tests does not establish a statistical production-crash probability without a justified model. One small lifecycle counterexample outweighs that count.

## Optional strict comparator

`compare_observations.py BASELINE.json CANDIDATE.json` uses only the Python standard library. It reads data, does not import or execute the PR, and returns:

- `0`: all planned records are healthy under their supplied expectations and strictly equal;
- `1`: a mismatch, unhealthy record, failed assertion, or incompatible environment was detected;
- `2`: invalid input/schema or unreadable files.

The helper does not select cases, evaluate semantic oracles, measure coverage, or approve a merge. It cannot detect a falsely asserted invariant or a hazard omitted from the plan. An intended bug fix may correctly produce exit `1`; classify and validate that intended difference separately rather than weakening the unchanged-contract comparator. A required case cannot be removed from the plan merely to obtain exit `0`.

Each file uses this schema:

```json
{
  "schema_version": 1,
  "revision": "exact-pinned-commit-or-tree",
  "environment": {"runtime": "version", "backend": "explicit-name"},
  "case_ids": ["empty-index/query"],
  "observations": [
    {
      "id": "empty-index/query",
      "status": "ok",
      "expect": "ok",
      "value": {"shape": [1, 0], "dtype": "float32", "values": []},
      "checks": {"shape_matches_contract": true},
      "warnings": []
    }
  ]
}
```

`checks` must include at least one independently evaluated boolean contract check for success; all must be true. `warnings` is required; list them rather than swallowing them. The helper treats warnings as unhealthy unless the record contains exactly matching `expected_warnings`, defined from the contract before running the case. Both sides must use the same expectations. Do not auto-copy observed warnings into expected warnings.

An intended-error case uses `expect: "error"`, `status: "error"`, and `error: {"type": "ValueError", "code": "INVALID_K", "message": "..."}`. Supply `expected_error` with the required type and either an exact diagnostic code or exact message; broad exception-type matching alone is insufficient. `checks` can additionally validate cleanup/state after rejection. `timeout`, `crash`, and `skipped` records are always unhealthy in a required case. For unexpected errors, record `expect: "ok"`; never relabel the observation as an expected error just to pass.

Record environment metadata relevant to compatibility, excluding checkout location/revision (those differ intentionally). Different environments are reported as noncomparable. Keep source paths, versions, commands, case rationale, and native diagnostic configuration in the wider evidence bundle. The schema's revision field is a label; the reviewer must verify it against the checkout.

## Finding triage

For each finding include:

1. Severity and concrete trigger, including necessary prior state/configuration.
2. Expected versus actual behavior and whether it is a new regression, incomplete fix, inherited defect, or environment/harness problem.
3. Causal changed lines and a runnable minimal reproduction with observed exception/signal/output.
4. Impacted public APIs/backends/persistence modes and the operational consequence.
5. Narrow corrective requirement and a regression test that fails before correction and passes after it.

Do not inflate multiple failing manifestations into multiple root causes. Do not imply an actual production crash occurred merely because diagnostic bounds checks expose an invalid access. Report proven behavior separately from the inferred production consequence.

## Merge gates

Recommend **hold / changes required** when any of these is material to the affected supported path:

- reproduced crash, corruption, wrong result, invalid state, or unexpected exception;
- newly accepted input whose downstream lifecycle is broken;
- unresolved out-of-bounds/native diagnostic, resource leak, race, hang, or service-budget regression;
- relevant compatibility or rolling-update behavior remains unverified;
- required checks failed, timed out, were skipped/unavailable, or do not exercise the actual backend;
- the tested tree is stale, merge conflicts/resolutions are untested, or the harness cannot distinguish real outputs from artifacts.

Recommend **ready for the tested scope** only when the exact prospective merge is current, the planned required obligations have observable passing evidence, intentional differences are correct, adversarial findings have been resolved and retested, and remaining limitations are nonmaterial to the proposed deployment scope. Explain the scope restriction explicitly. If evidence is insufficient, continue useful local investigation; report the specific remaining gap rather than declaring a PR safe from green CI.

There is no waiver for “only an edge case” if a supported workflow can reach it. Conversely, distinguish an unsupported malformed input from a promised contract and an inherited bug from a candidate regression. Do not turn this skill into a requirement to fix every unrelated legacy issue before a focused PR can merge.

## Review bundle and author reply

Save a review bundle with revision/environment manifests, the risk/obligation plan, original and minimized tests, raw results, differential summary, and final verdict. Record exact commands, seed, observed versus planned case counts, test counts, failures/errors/skips, native process outcomes, and platform gaps. A temporary test file is useful even when it fails; retain it for reruns after the author updates.

The user-facing review should lead with the verdict, then actionable findings, then a concise test summary. If authorized to post, include the minimal reproduction, the requested correction and permanent tests, and actual evidence. Every agent-authored GitHub publication must end with the agent's full name/role and verified model/version, following SKILL.md's GitHub attribution rule. If that identity cannot be verified, resolve it before publishing; do not invent a version. Ordinary chat replies need no signature. Do not include credentials, internal data, inaccessible local paths, or an unconditional no-regression guarantee in public replies.

On a new head or target update, reread the entire changed diff, retest affected cases, and repeat relevant broad checks. Keep old results labeled as old evidence. A final CI success must correspond to the reviewed code; an approval on a prior SHA is not validation of a later commit.
