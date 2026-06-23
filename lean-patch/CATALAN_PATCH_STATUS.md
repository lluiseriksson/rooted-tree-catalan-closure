# Catalan patch status

**Artifact version:** 1.3.0

**Formal status:** checked conditional adapter; general Catalan identity remains open.

## Pinned environment

- Base snapshot: `1d044a353ac2b69ddca732dd851fb0ab4a94d7af`
- Checked patch commit: `d668c333db302f9f399374e3c824805a1c4d71da`
- Lean: `leanprover/lean4:v4.29.0-rc6`
- Mathlib: `07642720480157414db592fa85b626dafb71355b`

## Certified in the archived adapter

- `YangMills.KP.RootedChildFactorialCatalanIdentity` names the exact replacement point.
- `YangMills.RG.catalanClosure_fixedPoint` proves the square-root fixed-point identity.
- `YangMills.RG.catalanClosure_nonneg` proves nonnegativity in the stated small regime.
- `YangMills.RG.appendixFHoleHsharpWeightedTreeMarkedRootSum_le_catalan_of_expWeight`
  proves the marked-root Appendix-F bound conditional on the exact identity at order `n`.
- The oracle log reports only `[propext, Classical.choice, Quot.sound]`.
- The archived build log ends with `Build completed successfully (8235 jobs).`

## Not certified in this artifact

The proposition

```lean
YangMills.KP.RootedChildFactorialCatalanIdentity n
```

has not been proved for every `n` in Lean. This repository is therefore not a closed
formal proof of the exact general identity. It is a checked conditional downstream
adapter plus an exact statement of the remaining combinatorial obligation.

## Integrity and replay

`project.json` pins the critical recovered files by Git blob ID.
`scripts/check_repository.py` verifies those IDs, the active Lean placeholder policy,
the captured logs, and the claim boundary. CI checks that the mailbox patch applies to
the exact upstream base; `full-lean-replay.yml` performs the clean kernel replay.
