# Two failures that shaped this workflow

These examples are based on public BM25S PR reviews. Their lesson is about state and evidence, not a universal mandate to use BM25-specific APIs or error behavior. The same reasoning applies to readers, caches, search indexes, parsers, databases, and serializers.

## Empty file with a stale persisted index

A reader fix allowed genuinely zero-byte JSONL files to load without constructing an mmap. Ordinary non-empty tests and a large differential suite passed. The missed transition was:

`write nonempty corpus -> persist line index -> truncate corpus to zero -> reload`

Simply accepting the empty backing file exposed an old nonzero length, despite having no readable documents. A constructor-only empty-file test could not distinguish genuine empty state from a truncated previously indexed corpus.

The adversarial checks exercised fresh construction, reload on an existing object, and the public high-level loader with saved and in-memory indexes. Correct behavior accepted genuinely empty files, rejected a zero-byte source paired with nonempty index state immediately, and closed the file handle on failure. Empty integer access raised the normal out-of-range error.

A second review found an empty-file guard located after mmap construction, where the zero-byte construction error would already occur. Validation ordering matters: a visually reassuring guard may be unreachable at the failure point.

Source: [BM25S PR #206](https://github.com/xhluca/bm25s/pull/206). Reusable checks: persistence/mutation/reload, cross-representation invariants, cleanup, and guard reachability.

## Indexing succeeds but the index cannot be queried

A small empty-corpus fix suppressed mean/division warnings and seeded a missing empty token after the score matrix was constructed. Its added tests checked document count, empty score data, and the new vocabulary entry. All existing CI jobs passed.

For three token-less documents, indexing produced:

```text
num_docs = 3
vocab = {"": 0}
indptr = [0]
```

Token 0 had no score column: its end pointer would require `indptr[1]`. A normal text query raised a token-ID error. Querying the empty token under Numba raised an out-of-bounds `IndexError` with bounds checking enabled. Eager and mmap save/load preserved the malformed state. Reindexing the same `Tokenized` object changed `indptr` to `[0, 0]`, because the first call mutated the input vocabulary after matrix construction.

The independent validation found no differences in 74,512 paired observations across 5,400 configurations of previously supported behavior. Nonetheless, nine of 14 lifecycle checks failed, reflecting one root cause. The verdict was to hold the PR and ask for a valid zero-score column plus retrieval, persistence, and repeated-input regression tests.

A harness initially reported false differences because it serialized object arrays with `tobytes()`, which captured pointers to Python objects. Switching to recursively serialized values removed those artifacts. Investigating the harness is part of the review; a difference is not automatically a code regression.

Source: [BM25S PR #202 review comment](https://github.com/xhluca/bm25s/pull/202#issuecomment-6082619351), reviewing head `f94a97b` combined with the then-current target. This is historical review evidence, not a statement about any later PR head.

## Applying the lessons

- Producer success is insufficient: test its consumers and persisted lifecycle.
- New input support needs an independent validity contract; baseline rejection does not prove candidate success is correct.
- Huge passing comparisons cannot outweigh a reachable state inconsistency.
- Reuse the same input object to reveal post-construction mutation and aliasing.
- Native bounds diagnostics can expose failures hidden by ordinary runs.
- Separate genuine differences, harness artifacts, inherited failures, and intended improvements.
