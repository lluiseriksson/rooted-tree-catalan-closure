# Claims boundary

## Certified and recovered

- Canonical manuscript source and compiled PDF are present and integrity-pinned.
- The exact Lean replacement point is named by
  `YangMills.KP.RootedChildFactorialCatalanIdentity`.
- The square-root closure and its nonnegativity theorem are checked in Lean.
- The marked-root Appendix-F adapter is checked conditional on the exact Catalan identity.
- Captured oracle reports contain only `[propext, Classical.choice, Quot.sound]`.
- The mailbox patch is automatically checked against the immutable upstream base.
- Release archives are deterministic, checksummed, SBOM-described, and independently verified.
- Exact finite computations agree with `n! · Catalan(n)` for `0 ≤ n ≤ 8`; direct
  complete-graph tree enumeration is also performed through `n = 7`.

## Not certified here

- A general Lean proof of `RootedChildFactorialCatalanIdentity n` for every `n`.
- A formalized Prüfer equivalence and degree/multiplicity theorem sufficient to close it.
- The model-specific raw Yang–Mills activity estimate.
- A continuum construction, Osterwalder–Schrader reconstruction, or mass gap.
- Merger of the conditional patch into the upstream project.

The finite checker is exact and independently useful, but finite evidence is not a
substitute for the still-open general Lean theorem. Operational recovery completeness
must not be confused with completion of the remaining formal obligation.
