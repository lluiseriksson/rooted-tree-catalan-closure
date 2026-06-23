# Changelog

## 1.5.0 - 2026-06-23

- Replaced brittle whole-workflow blob locks with semantic GitHub Actions policy checks.
- Pinned every external action to a full commit SHA and upgraded checkout, setup-python,
  and upload-artifact to their reviewed current major lines.
- Grouped future GitHub Actions updates into one Dependabot pull request and made
  high/critical dependency-review findings blocking.
- Preserved archived Lean build and oracle logs inside the deterministic source ZIP.
- Added extracted source-tree self-audit to release verification, closing a gap where a
  package could match its manifest yet omit files required for standalone verification.
- Added supply-chain documentation and regression tests for action pins and archived logs.

## 1.4.1 - 2026-06-23

- Rebased the upgrade guard onto `e50d83f5f2ebd2cce8d470f39dbeba5fa20f4ff6`, preserving the successful CI source-pin fix.
- Hard-pinned `TEX := main.tex` and the tracked PDF name, with audit and unit-test regression guards.
- Added a Python 3.11/3.12/3.13 tooling matrix and portability documentation.
- Added exact finite Catalan checks by Prüfer words, direct complete-graph tree
  enumeration, and Prüfer occurrence profiles.
- Added deterministic finite evidence through `n = 8` and a machine-readable theorem
  manifest.
- Documented the Prüfer-profile cancellation that narrows the remaining Lean proof.
- Added pinned upstream bootstrap scripts for POSIX shells and PowerShell.
- Added machine-readable full Lean replay reports and stricter replay pin validation.
- Stopped ordinary paper builds from overwriting the tracked recovered PDF.
- Switched release ZIPs to `ZIP_STORED` for cross-runtime byte determinism and added
  release/source parity verification plus file-level SPDX license records.
- Hardened CI, release attestation guards, local link checks, JSON/Python validation, and
  release metadata cross-checks.
- Added a verified full-history Git bundle, ref inventory, disaster-recovery guide,
  metadata schema, CI backup workflow, and integration test covering restoration.

## 1.3.0 - 2026-06-23

- Added immutable Git-blob verification for the recovered primary materials.
- Replaced the lightweight audit with a full provenance, placeholder, axiom, evidence,
  workflow, metadata, and claim-boundary audit.
- Added deterministic package replay and independent release verification.
- Added SPDX 2.3 SBOM and release metadata output.
- Added patch-application CI against the exact upstream base and a manual full Lean replay.
- Added tag-driven release automation, Dependabot, contribution policy, templates,
  CodeMeta, Zenodo metadata, and a release checklist.
- Removed the installer script from the repository itself and retired the duplicate
  `artifact.yml` workflow.

## 1.2.0 - 2026-06-23

- Added machine-readable project metadata and recovery provenance.
- Added explicit claims boundary, recovery log, reproducibility notes, and documentation license.
- Added static artifact audit and deterministic source packaging scripts.
- Added GitHub Actions workflow for audit/package/paper checks.
- Hardened README, Makefile, `.gitignore`, `.gitattributes`, and Lean patch manifest.
- Kept the Lean claim boundary conditional: the exact Catalan identity remains open.

## 1.1.0 - 2026-06-22

- Added checked conditional Lean adapter bundle and captured oracle/build logs.

## 1.0.0 - 2026-06-22

- Initial rooted-tree Catalan closure paper bundle.
