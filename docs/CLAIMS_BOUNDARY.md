# Claims boundary

This repository is a recovered publication artifact for the rooted-tree Catalan closure
argument and its Lean 4 adapter.

## Certified in this repository

- The paper source and compiled PDF are present.
- The Lean patch states the exact Catalan replacement point as
  `YangMills.KP.RootedChildFactorialCatalanIdentity`.
- The square-root Catalan closure theorem is checked in the recorded patch bundle.
- The Appendix-F marked-root leaf summation adapter is checked conditionally on the
  Catalan identity.
- The oracle log records only `[propext, Classical.choice, Quot.sound]` for the listed
  conditional adapter declarations.

## Not certified here

- A closed proof of `RootedChildFactorialCatalanIdentity n` for every `n`.
- A proof of the model-specific raw Yang--Mills activity estimate.
- A continuum limit, Osterwalder--Schrader reconstruction, or Yang--Mills mass gap.
- A claim that the conditional patch has been merged into the upstream project.

This boundary is intentional: it prevents the repository from overstating the present
formal status while keeping the downstream adapter reproducible and reviewable.
