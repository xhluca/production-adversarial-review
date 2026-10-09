# Production Adversarial Review

A Codex skill for reviewing production pull requests under the assumption that a production crash costs **$1,000,000 per day**.

The review attempts to falsify a PR's claims through targeted lifecycle tests, differential comparisons, and independent contract checks. It requires evidence for the exact prospective merge and holds changes that introduce a material defect or leave a newly accepted workflow broken. Passing tests do not prove zero production risk.

## Install

Clone into a new skill directory; do not overwrite an existing installation:

```sh
git clone https://github.com/xhluca/production-adversarial-review.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/production-adversarial-review"
```

The repository already contains `agents/openai.yaml` in the correct location. No file rearrangement is needed. In a Codex session where the skill is available, invoke:

> Use $production-adversarial-review to review this PR against current main. Assume a production crash costs $1M/day. Reproduce adversarial failures and give an evidence-backed merge recommendation.

For a fixed version, check out the corresponding release tag after cloning. Inspect updates before pulling them into an installed skill.

## Package

| File | Purpose |
| --- | --- |
| [SKILL.md](SKILL.md) | Review workflow, scope, authorization boundaries, and merge gates |
| [CHECKS.md](CHECKS.md) | Lifecycle, persistence, numerical, native, backend, concurrency, resource, and compatibility checks |
| [EVIDENCE.md](EVIDENCE.md) | Evidence schema, differential-harness rules, triage, and decision criteria |
| [CASE_STUDIES.md](CASE_STUDIES.md) | Two public PR failures and a false-difference harness failure |
| [compare_observations.py](compare_observations.py) | Strict comparison helper using only the Python standard library |
| [test_compare_observations.py](test_compare_observations.py) | Failure-mode tests for the helper |
| [agents/openai.yaml](agents/openai.yaml) | Codex UI metadata |

The skill covers state creation followed by downstream use, save/reload, source mutation and stale indexes, repeated caller-owned inputs, optimized and fallback paths, and native diagnostics. Checks are selected from the actual diff and supported workflows rather than an arbitrary test quota.

## Run the helper tests

Requires Python 3.10 or later; no third-party dependencies:

```sh
python3 -m unittest -v test_compare_observations
```

GitHub Actions runs these tests on Python 3.10 and 3.12 for pushes and pull requests.

## Compare review evidence

Prepare files using the schema in [EVIDENCE.md](EVIDENCE.md), then run:

```sh
python3 compare_observations.py baseline.json candidate.json
```

The helper rejects incomplete case sets and flags shared crashes, skips, unexpected exceptions/warnings, failed contract checks, environment differences, and result mismatches. Exit `0` means strict healthy equality, `1` means differences or unhealthy evidence, and `2` means invalid input. It never approves a merge, executes contributor code, or performs network calls.

The reviewer still has to choose meaningful cases, evaluate independent oracles, validate intended differences and newly accepted inputs, and verify the actual checked-out revisions. The reviewed project's tests require that project's own dependencies and an appropriately isolated environment.

The original [v1.0.0 Gist](https://gist.github.com/xhluca/9e51330610258c0fececf9570616a7b3) remains available; this repository is the maintained distribution.
