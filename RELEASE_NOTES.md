# Release notes

## v1.6.0 standalone ZIP verification and exact history inventory

This release extends the v1.5.1 repackaging work with an archive-first recovery path. The
original ZIP can now be verified without extracting it and without assuming that Windows
preserves Unix executable bits. It also closes two silent-normalization gaps: duplicate JSON
keys and history inventories that were checksummed but not compared with the refs actually
advertised by the Git bundle.

### Added

- `scripts/verify_source_zip.py`, a standalone verifier for source ZIP bytes, external
  checksums, canonical entry order, timestamps, portable modes, paths, CRCs, manifest hashes,
  release identity, and bounded archive resources.
- `scripts/strict_json.py`, which rejects duplicate object keys and `NaN`/infinite values in
  integrity-critical metadata.
- History inventory schema 2 with the exact output of `git bundle list-heads`, including
  `HEAD`, annotated-tag object IDs, and `refs/rtc-recovery/HEAD`.
- `make verify-source-zip` and CI coverage on the reference packaging job.
- Regression tests for Windows-style permission loss, mode drift, duplicate JSON keys,
  checksum-name substitution, and history-head inventory tampering.

### Hardened

- Safe extraction restores Unix modes only on POSIX; Windows host modes are explicitly
  non-authoritative because archive metadata was already checked.
- Source ZIPs have file-count, per-file-size, and total-expanded-size ceilings.
- Portable filename validation includes UTF-8 length limits and additional Windows device
  names.
- Release metadata schema 4 records the standalone command, permission model, resource
  limits, history inventory schema, and exact-head verification requirement.
- `verify_release.py` runs the standalone verifier before extraction and independently
  cross-checks its report against the manifest, SBOM, release metadata, and source tree.

### Formal boundary

The engineering and recovery layers are stronger, but the theorem boundary is unchanged.
`YangMills.KP.RootedChildFactorialCatalanIdentity n` remains an explicit open general Lean
obligation. No local axiom, `sorry`, or finite-computation overclaim is introduced.
