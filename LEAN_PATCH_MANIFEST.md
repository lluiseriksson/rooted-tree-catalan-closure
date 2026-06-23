# Lean 4 patch manifest

This manifest is a specification and recovery record for the narrow Catalan patch. It is
not a claim that the remaining exact Catalan bijection has been fully proved. The checked
part of the artifact is the downstream adapter that takes the Catalan identity as an
explicit hypothesis.

## Base snapshot

- Repository: `lluiseriksson/THE-ERIKSSON-PROGRAMME`
- Base commit inspected: `1d044a353ac2b69ddca732dd851fb0ab4a94d7af`
- Checked mailbox patch commit: `d668c333db302f9f399374e3c824805a1c4d71da`
- Lean: `leanprover/lean4:v4.29.0-rc6`
- Mathlib: `07642720480157414db592fa85b626dafb71355b`

## Adapter modules

1. `YangMills/KP/RootedCatalan.lean`
2. `YangMills/RG/AppendixFHsharpCatalanClosure.lean`
3. `YangMills/RG/AppendixFHsharpCatalanSource.lean`

Repository-local copies are stored under `lean-patch/`, together with
`lean-patch/catalan-conditional-adapter.patch`.

## Verified declarations

- `YangMills.KP.rootedChildCount_factorialTreeSum_normalized_le_catalan_of_identity`
- `YangMills.RG.catalanClosure_fixedPoint`
- `YangMills.RG.appendixFHoleHsharpWeightedTreeMarkedRootSum_le_catalan_of_expWeight`

`lean-patch/verification/oracle_check_catalan.log` records only
`[propext, Classical.choice, Quot.sound]` for those declarations. Their structured status
is in `archive/theorem-manifest.json`.

## Exact finite evidence

`scripts/check_finite_catalan.py` independently checks the unnormalised identity through
`n = 8` using Prüfer words and occurrence profiles, and through `n = 7` by direct
complete-graph tree enumeration. The deterministic table is
`evidence/finite-catalan-checks.json`.

These checks are not a proof for all `n`. They strengthen the executable specification
and expose the short Prüfer-profile reduction documented in
`docs/PRUFER_PROFILE_REDUCTION.md`.

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

Every closed theorem should report only `[propext, Classical.choice, Quot.sound]`, with
no `sorryAx` and no project-specific axioms.
