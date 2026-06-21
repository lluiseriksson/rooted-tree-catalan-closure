# Rooted-tree summation and Catalan closure

This repository contains the LaTeX source, compiled PDF, and Lean 4 patch manifest for
the rooted-tree Catalan closure note.

## Status

The paper proves the mathematical Catalan replacement and records the Lean 4 interface
that should replace the existing geometric `4^n` closure.  This package does not claim
that the Catalan patch has already been archived as a verified Lean commit.  That claim
should be added only after the exact commit builds and its axiom report is included.

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
of child factorials and the geometric `4^n` closure.  The exact Catalan theorem,
square-root closure, and downstream adapters form the narrow patch specified in the
paper.

A verified archival artifact should record the exact Catalan patch commit and run:

```sh
lake exe cache get
lake build YangMillsCore
lake env lean oracle_check.lean
python scripts/check_consistency.py
```

The manuscript does not assert that an unarchived patch has already passed those checks.
