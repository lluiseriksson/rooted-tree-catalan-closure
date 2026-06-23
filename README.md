# Rooted-tree summation and Catalan closure

[![Artifact audit](https://github.com/lluiseriksson/rooted-tree-catalan-closure/actions/workflows/artifact.yml/badge.svg)](https://github.com/lluiseriksson/rooted-tree-catalan-closure/actions/workflows/artifact.yml)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/code-AGPL--3.0--or--later-blue.svg)](LICENSE)
[![Manuscript: CC BY 4.0](https://img.shields.io/badge/manuscript-CC%20BY%204.0-lightgrey.svg)](docs/LICENSE.md)

This repository contains the LaTeX source, compiled PDF, Lean 4 patch manifest, and a
checked **conditional** Lean adapter for the rooted-tree Catalan closure note.

## Current status

The artifact is recovered as a publication bundle plus a verified downstream adapter.
The Lean material is deliberately honest about the remaining gap: it does **not** yet
prove the full exact Catalan identity

```lean
YangMills.KP.RootedChildFactorialCatalanIdentity n
```

for every `n`.  Instead, the downstream Appendix-F adapter assumes that identity as an
explicit theorem hypothesis and verifies the square-root closure and marked-root
adapter on top of it.

Recorded Lean provenance:

- Base commit: `1d044a353ac2b69ddca732dd851fb0ab4a94d7af`
- Checked patch commit recorded by the bundle: `d668c333db302f9f399374e3c824805a1c4d71da`
- Lean toolchain: `leanprover/lean4:v4.29.0-rc6`
- Mathlib: `07642720480157414db592fa85b626dafb71355b`

New/patch modules:

- `lean-patch/YangMills/KP/RootedCatalan.lean`
- `lean-patch/YangMills/RG/AppendixFHsharpCatalanClosure.lean`
- `lean-patch/YangMills/RG/AppendixFHsharpCatalanSource.lean`
- `lean-patch/catalan-conditional-adapter.patch`
- `lean-patch/oracle_check_catalan.lean`

See `lean-patch/CATALAN_PATCH_STATUS.md`, `docs/CLAIMS_BOUNDARY.md`, and
`docs/RECOVERY.md` for the exact certification boundary.

## Build, audit, and package

Build the paper:

```sh
make paper
```

Run the repository audit:

```sh
make audit
```

Create a deterministic source package:

```sh
make package
```

On Windows, with `tectonic.exe` available on `PATH`, run:

```powershell
.\build.ps1
```

The bibliography is embedded directly in `main.tex`; no BibTeX or Biber step is needed.

## Lean artifact boundary

The inspected upstream snapshot already contains the fixed-tree estimate with the product
of child factorials and the geometric `4^n` closure.  The current patch proves the
square-root closure and a downstream Appendix-F adapter assuming the exact Catalan
identity as an explicit hypothesis.  The missing remaining obligation is the general
rooted child-factorial Catalan bijection.

For the conditional adapter, the checked commands recorded in this bundle are:

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
