# Changelog

## 1.8.0 - 2026-06-23

- Corrected source-ZIP Unix metadata to include the regular-file type bit together with
  canonical `0644`/`0755` permissions and filename-dependent UTF-8 flags.
- Added producer-side archive ceilings and immediate standalone verification of every source
  ZIP before its SBOM and release metadata are emitted.
- Required canonical, sorted, newline-terminated JSON for tracked and generated
  integrity-critical metadata, closing whitespace/order normalization ambiguity.
- Upgraded history inventory to schema 3: bundles are mirror-restored in an isolated Git
  environment, checked with `git fsck --full --strict`, compared against the exact restored
  ref set, and bound to the annotated `v<version>` tag at `HEAD`.
- Hardened manuscript inspection with the exact archived 17-page A4/PDF-1.5 identity,
  an explicit PDF-1.5/PDF-1.7 rebuild allowlist, one PDF revision, no trailing payload,
  and no encryption, JavaScript, forms, actions, or embedded files.
- Added regression coverage and machine-audited policy/schema fields for the new ZIP, JSON,
  PDF, and Git recovery invariants.

## 1.7.0 - 2026-06-23

- Restricted publication packages to tracked regular files from a clean Git worktree;
  untracked files are excluded and tracked symbolic links or missing/non-regular paths fail
  closed.
- Added a canonical complete-release `SHA256SUMS` file and exact regular-file output
  inventory, including symbolic-link rejection for release destinations and verification.
- Made the SPDX 2.3 SBOM conformant for analyzed files with canonical SHA-1 plus SHA-256
  checksums and the independently verified package verification code.
- Extended strict JSON parsing to reject exponent overflow and underflow, and extended
  portable-path checks to reject Unicode control, formatting, surrogate, and line-separator
  characters.
- Made the PowerShell paper build non-destructive by default and added an explicit tracked-PDF
  refresh switch plus PDF inspection.
- Made `make verify` include independent release verification and expanded metadata, schema,
  audit, documentation, and regression coverage for all new publication invariants.

## 1.6.0 - 2026-06-23

- Added a standalone source-ZIP verifier that validates archive bytes, canonical modes,
  timestamps, paths, CRCs, resource limits, the internal manifest, and the optional
  external checksum without trusting permissions produced by the host extractor.
- Made safe extraction explicitly permission-independent on Windows while retaining the
  normalized executable policy in ZIP metadata.
- Added strict JSON decoding for integrity-critical metadata, rejecting duplicate keys and
  non-finite numbers that the default Python decoder would otherwise accept silently.
- Upgraded history inventories to schema 2 and now compare the recorded inventory exactly
  with `git bundle list-heads`, including `HEAD` and the detached-head recovery ref.
- Added archive file-count/size ceilings, extended portable filename checks, release metadata
  schema 4, CI coverage, documentation, and regression tests for all new invariants.

## 1.5.1 - 2026-06-23

- Fixed second-generation source packaging: an extracted release no longer re-adds
  `SOURCE-MANIFEST.sha256` and create a duplicate ZIP entry.
- Centralized source inventory filters so Git checkouts and extracted archives select the
  same distributable files.
- Added strict portable-path, case-collision, ZIP metadata, SPDX inventory, and manifest
  validation with safe manual extraction instead of `extractall`.
- Added an autonomous extracted-source manifest verifier and made the repository self-audit
  run it whenever the generated manifest is present.
- Added cross-surface metadata checks for project, CFF, BibTeX, CodeMeta, Zenodo, changelog,
  release notes, theorem status, claim boundaries, and upstream pins.
- Added regression tests for archive traversal, Windows-reserved paths, malformed manifests,
  duplicate SPDX paths, extracted-source checksum drift, and metadata drift.

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
