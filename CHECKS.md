# Adversarial check design

Use this reference to turn the changed behavior into a targeted plan. The production-loss assumption requires thorough validation of affected contracts, not arbitrary quotas or a Cartesian explosion of unrelated settings.

## Identify the actual unit of risk

List the public entry points, producers/consumers of changed state, supported deployment configurations, and failure modes. A small diff can affect a large contract. Inspect callees, wrappers, exception boundaries, persistent formats, native consumers, and shared inputs. Changes in type, dtype, shape, ordering, mutability, exceptions, resource ownership, defaults, or error timing can break consumers even when values look similar.

For each plausible risk record:

| Field | Required content |
| --- | --- |
| Trigger | Concrete input plus prior state and configuration |
| Invariant | What must be true after success or failure |
| Oracle | Independent expected result or property |
| Consequence | Crash, wrong result, corruption, leak, hang, compatibility failure, or resource blow-up |
| Case | Minimal reproduction and targeted broader combinations |
| Baseline | Supported behavior, known failure, or not applicable |
| Evidence | Exact command/tree, status, artifact, and any remaining gap |

Prioritize severity, likelihood, exposure, and detectability. Silent corruption may have a larger blast radius than an immediate rejection. Do not invent probabilities, deployment scale, or financial-loss estimates to make the result look quantified.

## Lifecycle families

### Created state must be usable

Exercise `create/index/parse -> query/read/serialize/update` via the public API. Validate the consumer, not only the producer's return value. Empty collections, zero rows, zero columns, empty strings, unknown keys/tokens, and all-filtered inputs must keep metadata and data structures consistent.

Check redundant representations: counts match actual lengths; all valid IDs have corresponding storage; column pointers have the required terminal entry; pointer/offset sequences are monotonic and in range; auxiliary arrays cover the IDs their consumers access. Check dimensions and semantic alignment, not only `.size == 0`.

Distinguish no documents from documents with no tokens, no queries from an empty query, and an empty selection from a rejected invalid request. These states often follow different branches. Test both string-like inputs and encoded/object forms if supported; include independently created empty input objects rather than reusing a mutated vocabulary across cases.

### Persistence and stale state

Exercise:

1. `create -> use -> save -> close -> reload -> use` in eager and lazy/mmap modes.
2. `persist index/cache -> mutate or truncate backing data -> fresh constructor -> use`.
3. The same mutation through an existing object's reload method and high-level loader.
4. Delete or alter sidecars/auxiliary files; use partial/truncated files and incompatible metadata when implicated.
5. Failure then correction then retry; cleanup then repeated cleanup; reopen after failure.

Check immediate rejection versus deferred failure, exception quality, actual count/content, and file-handle cleanup. A stale nonzero count with empty backing data is not a valid empty result. When file replacement and caching matter, test the documented consistency policy; do not assume that appending, replacing, and truncating are interchangeable.

For binary/mmap readers, isolate invalid accesses in child processes. Verify reported sizes before dereferencing. If a mutation can invalidate a live mapping, use a disposable process and fixture rather than risking the reviewer's session.

### Reuse, aliasing, and failure atomicity

Reuse the same caller-owned input object twice and compare against equivalent fresh inputs. Check whether successful indexing mutates a vocabulary/list/array, and whether a second call changes the generated state. Test transitions `normal -> empty -> normal`, changes in configuration, repeated saves, reloads, and retries.

When atomicity is promised or relied upon, snapshot existing state, inject a bounded failure, then verify either complete old state or complete new state. A failed operation must not leave misleading success metadata, poisoned caches, partially installed pointers, or leaked resources. Test failures at meaningful write/commit boundaries rather than every implementation line.

## Boundary and representation families

- Test zero, one, boundary-minus-one, boundary, and boundary-plus-one for sizes, IDs, offsets, capacity, `k`, chunk size, or thread count as applicable.
- Include negative, too-large, missing, and invalid inputs only where the API accepts or promises to reject them; preserve rejection semantics and timing.
- Check output shape and dtype, integer width, precision, signedness, scalar versus array results, object versus numeric arrays, and mutable versus immutable return types.
- Include repeated/unknown items, all ties, all zeros, mixed empty/non-empty data, and asymmetric dimensions. Include negative/NaN/infinite values when their acceptance/rejection matters.
- For strided/noncontiguous/read-only views, endian differences, Unicode, embedded delimiters, or encodings, test only when a supported caller can supply them or the changed path processes them.
- Check complete error contracts: type, actionable diagnostic/code, cleanup, and preserved object state. Matching broad exception types can hide unrelated errors.

Build a compact matrix of affected scoring/algorithm variants, storage modes, representations, dtypes, backends, and concurrency settings. Cover individually significant combinations fully. Pairwise/random exploration can supplement this; it cannot replace an interaction known to be hazardous. Record seeds and denominators. Cross-product cases that differ only in irrelevant settings do not add independent confidence.

## Numerical and selection families

Use exact comparisons for unchanged discrete contracts and deterministic algorithms. Choose numerical tolerances from precision/algorithm error or an established contract, before inspecting a discrepancy. Report maximum absolute/relative error and its worst input. Do not loosen tolerances until a failure disappears.

Check warnings and exception modes together, finite values, bounded/monotonic scores where mathematically warranted, aligned IDs/scores, in-range and nonduplicated selected IDs when required, and zero-sized result shape/dtype. Test selection at `k=0`, `k=1`, `k=n`, and `k>n`, and negative `k` according to the API.

For ties, compare exact order only when deterministic tie-breaking is promised; otherwise compare allowed sets and scores while still enforcing alignment and cardinality. Do not sort arbitrary outputs merely to hide an ordering regression. For weights/masks, verify filtered documents and transformations through an independent expected result.

Use small hand-computable fixtures and a reference implementation that does not share the changed implementation's assumptions. Metamorphic tests can check domain-valid properties such as permutation equivalence or repeated-call equivalence; justify each property rather than assuming an algebraic law the algorithm does not have.

## Optimized paths, concurrency, and resource families

### Optional dependencies and native execution

Force backend selection in tests; log which path actually executes. Check optimized and fallback behavior, optional dependency unavailable, installed but unusable, cold compilation, and warm execution where implicated. JIT disabled versus enabled is a separate configuration, not evidence of equivalence. Do not assume that importing Numba/JAX/another accelerator proves compiled code ran.

Use bounds checking, address/undefined-behavior sanitizers, debug allocators, or equivalent diagnostics for indexing/pointer changes. Keep those results separate from ordinary optimized runs. Native code can silently read invalid memory when Python would raise. Test unsafe-looking cases in restricted child processes with enforced timeouts and a documented memory budget.

### Concurrency

When shared state, execution dispatch, or thread-local settings change, test sequential and supported threaded/parallel modes, one versus multiple tasks, and repeated concurrent calls on shared and separate objects according to the API contract. Use barriers or controlled interleavings to exercise the disputed window; random stress alone is weak evidence.

Verify result integrity, absence of deadlock, restoration of global/thread-local settings after exceptions, and race-free ownership of buffers/caches. Avoid process-wide thread setting changes that leak into unrelated tests. Log actual worker/thread counts and terminate only child processes owned by the test harness.

### Resources and performance

For changes in allocation, copying, loops, batching, mmap, compilation, or I/O, test representative small and production-shaped synthetic workloads. Measure peak memory/retained memory, file descriptors, latency/throughput, and cleanup when material. Separate setup/cold compilation from warm steady state. Compare matched environments, enough repetitions to establish variability, and predetermined limits based on service budgets when available.

Test bounded out-of-memory/disk-full/I/O-error/interruption/timeout scenarios through fault injection or local substitutes when the path is affected. An unavailable platform-specific injector is a recorded gap, not a pass. Never exhaust the shared host's disk or memory, globally kill processes, or inject faults into real services.

## Compatibility and operational recovery

When format/schema/default/serialization behavior changes, exercise old artifacts under the candidate and, if rolling downgrade is supported, candidate artifacts under the old version. Check dependencies, parameter precedence, defaults, schema versioning, migration failure, and rollback state. Do not silently reinterpret unsupported versions or truncate data to make a loader succeed.

If the PR changes externally visible request behavior, test affected clients/adapters and bounded local error/retry scenarios. If it changes release/package contents, inspect the built artifact rather than only the checkout. Deployment and release tests are conditional on the assignment; do not expand a code review into an unauthorized rollout.
