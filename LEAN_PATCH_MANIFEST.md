# Lean 4 patch manifest

This manifest is a specification and recovery record for the narrow Catalan patch.  It
is not a claim that the remaining exact Catalan bijection has been fully proved.  The
checked part of the artifact is the downstream adapter that takes the Catalan identity
as an explicit hypothesis.

## Base snapshot

- Repository: `lluiseriksson/THE-ERIKSSON-PROGRAMME`
- Base commit inspected: `1d044a353ac2b69ddca732dd851fb0ab4a94d7af`
- Lean: `leanprover/lean4:v4.29.0-rc6`
- mathlib: `07642720480157414db592fa85b626dafb71355b`

## Proposed/adapter modules

1. `YangMills/KP/RootedCatalan.lean`
2. `YangMills/RG/AppendixFHsharpCatalanClosure.lean`
3. `YangMills/RG/AppendixFHsharpCatalanSource.lean`

The corresponding repository-local copies are stored under `lean-patch/`, together
with `lean-patch/catalan-conditional-adapter.patch`.

## Verified declarations recorded by the recovery bundle

- `YangMills.KP.rootedChildCount_factorialTreeSum_normalized_le_catalan_of_identity`
- `YangMills.RG.catalanClosure_fixedPoint`
- `YangMills.RG.appendixFHoleHsharpWeightedTreeMarkedRootSum_le_catalan_of_expWeight`

`lean-patch/verification/oracle_check_catalan.log` records only
`[propext, Classical.choice, Quot.sound]` for those declarations.

## Explicit remaining obligation

```lean
YangMills.KP.RootedChildFactorialCatalanIdentity n
```

must still be proved for every `n` before the artifact can be described as a closed
formal proof of the exact rooted child-factorial Catalan identity.

## Required checks for a closed archival patch

```sh
lake exe cache get
lake env lean YangMills/KP/RootedCatalan.lean
lake env lean YangMills/RG/AppendixFHsharpCatalanClosure.lean
lake env lean YangMills/RG/AppendixFHsharpCatalanSource.lean
lake build YangMillsCore
lake env lean oracle_check.lean
python scripts/check_consistency.py
```

Every closed theorem should report only `[propext, Classical.choice, Quot.sound]`,
with no `sorryAx` and no project-specific axioms.
