# Catalan patch status

Base snapshot: `1d044a353ac2b69ddca732dd851fb0ab4a94d7af`
Checked mailbox patch commit: `d668c333db302f9f399374e3c824805a1c4d71da`
Lean: `leanprover/lean4:v4.29.0-rc6`
Mathlib: `07642720480157414db592fa85b626dafb71355b`

This branch carries a checked, conditional Catalan adapter:

- `YangMills/KP/RootedCatalan.lean`
- `YangMills/RG/AppendixFHsharpCatalanClosure.lean`
- `YangMills/RG/AppendixFHsharpCatalanSource.lean`
- `oracle_check_catalan.lean`

## Certified here

- The exact Catalan replacement point is named as
  `YangMills.KP.RootedChildFactorialCatalanIdentity`.
- `YangMills.RG.catalanClosure_fixedPoint` is proved.
- The marked-root Appendix-F bound is proved conditional on
  `RootedChildFactorialCatalanIdentity n`.
- The captured oracle report contains only `[propext, Classical.choice, Quot.sound]`.
- Exact finite computations agree with the identity through `n = 8`, with independent
  direct tree enumeration through `n = 7`.

## Not certified here

This is not a closed formal proof. The general proposition

```lean
YangMills.KP.RootedChildFactorialCatalanIdentity n
```

remains open for arbitrary `n`. The finite checker is exact at the tested orders but is
not a substitute for the missing Lean proof. The artifact consists of a verified
downstream adapter, executable finite evidence, and a precise proof roadmap.

## Replay commands

```sh
lake exe cache get
lake build YangMillsCore
lake build YangMills.KP.RootedCatalan YangMills.RG.AppendixFHsharpCatalanClosure
lake build YangMills.RG.AppendixFHsharpCatalanSource
lake env lean oracle_check_catalan.lean
```
