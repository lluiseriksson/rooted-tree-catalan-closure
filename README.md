# Rooted-tree summation and Catalan closure

This repository contains the LaTeX source, compiled PDF, Lean 4 patch manifest, and a
checked conditional Lean adapter for the rooted-tree Catalan closure note.

## Status

The paper proves the mathematical Catalan replacement and records the Lean 4 interface
that should replace the existing geometric `4^n` closure.  The `lean-patch/` directory
contains a checked conditional adapter commit:

- Base commit: `1d044a353ac2b69ddca732dd851fb0ab4a94d7af`
- Patch commit: `d668c333db302f9f399374e3c824805a1c4d71da`
- New modules:
  `YangMills/KP/RootedCatalan.lean`,
  `YangMills/RG/AppendixFHsharpCatalanClosure.lean`,
  `YangMills/RG/AppendixFHsharpCatalanSource.lean`

This is not a closed formal proof of the exact Catalan identity.  The downstream
Appendix-F adapter is verified only conditional on
`YangMills.KP.RootedChildFactorialCatalanIdentity n`.  See
`lean-patch/CATALAN_PATCH_STATUS.md`.

## Build the paper

```sh
make paper
```

On Windows, with `tectonic.exe` available on `PATH`, run:

```powershell
.\build.ps1
```

The bibliography is embedded directly in `main.tex`; no BibTeX or Biber step is needed.

## Lean artifact boundary

The inspected base snapshot already contains the fixed-tree estimate with the product
of child factorials and the geometric `4^n` closure.  The current Lean patch proves the
square-root closure and a downstream Appendix-F adapter assuming the exact Catalan
identity as an explicit hypothesis.  The missing remaining obligation is the general
rooted child-factorial Catalan bijection.

For the conditional adapter, the checked commands are:

```sh
lake build YangMills.KP.RootedCatalan YangMills.RG.AppendixFHsharpCatalanClosure
lake build YangMills.RG.AppendixFHsharpCatalanSource
lake env lean oracle_check_catalan.lean
```

A fully verified archival artifact should additionally prove
`RootedChildFactorialCatalanIdentity n` for every `n` and then run:

```sh
lake exe cache get
lake build YangMillsCore
lake env lean oracle_check.lean
python scripts/check_consistency.py
```

The manuscript does not assert that the remaining exact Catalan identity has already
passed those checks.
