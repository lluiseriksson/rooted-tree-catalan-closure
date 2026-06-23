# Release notes

## v1.4.1 finite-evidence and replay hardening

This release moves beyond archival hardening and adds an independent executable check of
the central rooted-tree identity while preserving the formal claim boundary.

It is rebased onto the CI-green `e50d83f` master state, preserves the immediate Makefile source assignment, and tests the standard-library tooling on Python 3.11–3.13.

### Added

- Exact Prüfer-word checks through `n = 8`.
- Independent direct spanning-tree checks through `n = 7`.
- Exact occurrence-profile checks through `n = 8`.
- Deterministic evidence JSON and theorem manifest.
- A narrow Prüfer-profile Lean closure plan.
- Verified bootstrap scripts for the immutable upstream patch.
- Machine-readable full Lean replay reports.

### Release and CI improvements

- Paper builds now write under `build/` and cannot silently replace the recovered PDF.
- Source ZIPs use normalized `ZIP_STORED` entries, avoiding zlib-version-dependent bytes.
- Release verification compares the archive, manifest, SBOM, metadata, finite evidence,
  theorem manifest, and current source tree.
- Tagged attestations are guarded so manual dry runs do not publish provenance records.
- A complementary full-history Git bundle preserves commits and refs with checksums, a
  machine-readable inventory, structural verification, and tag-release publication.

### Formal boundary preserved

The exact finite computations do not close the general Lean theorem. The proposition
`YangMills.KP.RootedChildFactorialCatalanIdentity n` remains explicitly open for arbitrary
`n`; the downstream Lean adapter remains conditional on it.
