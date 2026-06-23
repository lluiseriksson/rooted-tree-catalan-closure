# Release notes

## v1.3.0 — archival integrity and replay hardening

This release upgrades the recovered bundle from basic CI and packaging to a complete
operational recovery gate.

### Added

- Critical Git-blob verification for all primary recovered materials.
- Full repository audit of active Lean placeholders, axioms, evidence, claims, pins,
  metadata, workflows, and PDF structure.
- Byte-for-byte deterministic packaging replay and independent release verifier.
- Internal source manifest, external checksum, SPDX 2.3 SBOM, and release metadata.
- Exact upstream patch-application CI and manually dispatched full Lean replay.
- Tag-driven release automation, CodeMeta/Zenodo metadata, Dependabot, issue/PR templates,
  contribution policy, provenance record, and release checklist.

### Preserved

The formal boundary remains unchanged: the downstream adapter is checked conditional on
`YangMills.KP.RootedChildFactorialCatalanIdentity n`; the general Lean proof is still open.
