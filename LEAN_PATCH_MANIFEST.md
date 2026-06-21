# Lean 4 patch manifest

This manifest is a specification for the narrow Catalan patch.  It is not a build log
and does not assert that the proposed modules have already been archived as a verified
Lean commit.

## Base snapshot

- Repository: `lluiseriksson/THE-ERIKSSON-PROGRAMME`
- Base commit inspected: `1d044a353ac2b69ddca732dd851fb0ab4a94d7af`
- Lean: `leanprover/lean4:v4.29.0-rc6`
- mathlib: `07642720480157414db592fa85b626dafb71355b`

## Proposed modules

1. `YangMills/KP/RootedCatalan.lean`
2. `YangMills/RG/AppendixFHsharpCatalanClosure.lean`
3. `YangMills/RG/AppendixFHsharpCatalanSource.lean`

## Headline declarations

- `rootedChildCount_factorialTreeSum_normalized_eq_catalan`
- `appendixFHoleHsharpWeightedTreeMarkedRootSum_le_catalan`
- `appendixFHoleHsharpWeightedTreeTerm_le_catalan`
- `catalanClosure_eq_tsum`
- `catalanClosure_fixedPoint`
- `catalanClosure_le_geometricClosure`
- `appendixFHoleHsharp_norm_le_catalanClosure`
- `rootedAppendixFHsharpProfile_of_catalanClosure`
- `singleScaleUVDecay_of_catalanProfile`

## Required checks for the archived patch

```sh
lake env lean YangMills/KP/RootedCatalan.lean
lake env lean YangMills/RG/AppendixFHsharpCatalanClosure.lean
lake env lean YangMills/RG/AppendixFHsharpCatalanSource.lean
lake build YangMillsCore
lake env lean oracle_check.lean
python scripts/check_consistency.py
```

Every headline declaration should report only
`[propext, Classical.choice, Quot.sound]`, with no `sorryAx` and no project-specific
axioms.
