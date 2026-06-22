# Catalan patch status

Base snapshot: `1d044a353ac2b69ddca732dd851fb0ab4a94d7af`

This branch adds a checked, conditional Catalan adapter:

- `YangMills/KP/RootedCatalan.lean`
- `YangMills/RG/AppendixFHsharpCatalanClosure.lean`
- `YangMills/RG/AppendixFHsharpCatalanSource.lean`
- `oracle_check_catalan.lean`

## Certified here

- The exact Catalan replacement point is named as
  `YangMills.KP.RootedChildFactorialCatalanIdentity`.
- The square-root closure theorem
  `YangMills.RG.catalanClosure_fixedPoint` is proved.
- The Appendix-F marked-root leaf summation adapter
  `YangMills.RG.appendixFHoleHsharpWeightedTreeMarkedRootSum_le_catalan_of_expWeight`
  is proved, conditional on `RootedChildFactorialCatalanIdentity n`.
- `oracle_check_catalan.lean` reports only
  `[propext, Classical.choice, Quot.sound]` for the new checked theorems.

## Not certified here

The general bijection proving

```lean
YangMills.KP.RootedChildFactorialCatalanIdentity n
```

for every `n` is not yet proved.  In particular, this branch is not a closed
formal proof of the exact rooted child-factorial Catalan identity.  It is a
verified downstream adapter plus a precise formal statement of the remaining
combinatorial obligation.

## Commands run

```sh
lake exe cache get
lake build YangMillsCore
lake build YangMills.KP.RootedCatalan YangMills.RG.AppendixFHsharpCatalanClosure
lake build YangMills.RG.AppendixFHsharpCatalanSource
lake env lean oracle_check_catalan.lean
```
