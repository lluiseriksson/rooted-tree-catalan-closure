# Computational evidence

`finite-catalan-checks.json` records exact finite checks of

```text
Σ_T ∏_v c_T(v)! = n! · Catalan(n)
```

for labelled complete-graph spanning trees rooted at `0`.

The evidence is regenerated and checked by:

```sh
make finite-check
```

Three integer-only methods are compared:

1. every Prüfer word through `n = 8`;
2. every `n`-edge subset of the complete graph that forms a tree through `n = 7`; and
3. every Prüfer occurrence profile through `n = 8`.

The tracked JSON is deterministic and includes a SHA-256 digest of its result table.
These computations strongly guard the statement and implementation against regression,
but they cover finitely many orders and are **not** a proof of the general Lean
proposition. The general Lean identity remains open, and the formal status is documented in
`docs/CLAIMS_BOUNDARY.md`.

The archived Lean adapter remains conditional on that still-open proposition.
