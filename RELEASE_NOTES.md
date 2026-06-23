# Release notes

## v1.7.0 clean-source publication and SPDX/output integrity

This release tightens the boundary between a development checkout and a publication
artifact. A source release is now built only from tracked regular files in a clean Git
worktree, and every emitted artifact is covered by an independently verified release
inventory. The SPDX document now carries the checksum profile required for an analyzed
SPDX 2.3 package while retaining SHA-256 as the release trust anchor.

### Added

- Tracked-only Git source discovery. Untracked, ignored, repository-internal, generated,
  symbolic-link, missing, and non-regular tracked paths cannot silently enter or disappear
  from a publication package.
- A clean-worktree publication gate in `scripts/package_release.py`. The explicit
  `--allow-dirty` option is limited to development builds and never includes untracked files.
- `rooted-tree-catalan-closure-v<version>.SHA256SUMS`, covering the ZIP, ZIP sidecar,
  SPDX document, and release metadata. Verification also requires the release directory to
  contain exactly the five declared regular-file outputs and no symbolic links.
- SPDX 2.3 file records with one canonical SHA-1 checksum plus SHA-256, together with the
  package verification code computed independently by the producer and verifier.
- Regression coverage for JSON exponent overflow and underflow, tracked symbolic links,
  redirected output paths, Unicode formatting characters in archive names, excluded paths,
  and checksum/SBOM tampering.

### Corrected

- Strict JSON parsing now rejects finite-looking exponent literals that Python would silently
  normalize to infinity or zero.
- The standalone ZIP verifier rejects repository-internal and generated source paths even
  when a forged internal manifest lists them.
- `build.ps1` writes and inspects the PDF under `build/` by default; replacing the tracked PDF
  requires the explicit `-RefreshTrackedPdf` switch.
- `make verify` now includes independent release verification, matching the documented local
  acceptance gate.
- The PowerShell build and release-output policy are now machine-audited and recorded in
  `project.json` schema 5 and release metadata schema 5.

### Formal boundary

The engineering and recovery layers are stronger, but the theorem boundary is unchanged.
`YangMills.KP.RootedChildFactorialCatalanIdentity n` remains an explicit open general Lean
obligation. No local axiom, `sorry`, or finite-computation overclaim is introduced.
