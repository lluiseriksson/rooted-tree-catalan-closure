# Lean 4 patch manifest

This manifest records the implemented, checked conditional adapter and separates it
from future theorem targets. It does not claim that the remaining exact Catalan
bijection has been formalized.

## Pinned environment

- Upstream repository: `lluiseriksson/THE-ERIKSSON-PROGRAMME`
- Base commit: `1d044a353ac2b69ddca732dd851fb0ab4a94d7af`
- Checked adapter commit: `d668c333db302f9f399374e3c824805a1c4d71da`
- Lean: `leanprover/lean4:v4.29.0-rc6`
- Mathlib: `07642720480157414db592fa85b626dafb71355b`

## Recovered adapter modules

1. `YangMills/KP/RootedCatalan.lean`
2. `YangMills/RG/AppendixFHsharpCatalanClosure.lean`
3. `YangMills/RG/AppendixFHsharpCatalanSource.lean`
4. `oracle_check_catalan.lean`

Repository-local copies are under `lean-patch/`; the mailbox patch is
`lean-patch/catalan-conditional-adapter.patch`.

## Checked declarations

- `YangMills.KP.rootedChildCount_factorialTreeSum_normalized_le_catalan_of_identity`
- `YangMills.RG.catalanClosure_fixedPoint`
- `YangMills.RG.catalanClosure_nonneg`
- `YangMills.RG.appendixFHoleHsharpWeightedTreeMarkedRootSum_le_catalan_of_expWeight`

The archived oracle output reports exactly `[propext, Classical.choice, Quot.sound]` for
the listed oracle endpoints.

## Explicit remaining obligation

```lean
YangMills.KP.RootedChildFactorialCatalanIdentity n
```

must be proved for every `n` before this can be described as a closed Lean proof of the
exact rooted child-factorial Catalan identity.

## Closed-artifact replay gate

```sh
lake exe cache get
lake build YangMillsCore
lake build YangMills.KP.RootedCatalan YangMills.RG.AppendixFHsharpCatalanClosure
lake build YangMills.RG.AppendixFHsharpCatalanSource
lake env lean oracle_check_catalan.lean
python scripts/check_consistency.py
```

Every closed theorem must remain free of `sorryAx` and project-local axioms.
