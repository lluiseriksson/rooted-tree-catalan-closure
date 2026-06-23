# Release notes

## v1.8.0 canonical archive metadata and deep recovery verification

This release fixes an interoperability defect in earlier source ZIPs: entries carried Unix
permission bits but not the Unix regular-file type bit. It also upgrades the two recovery
layers from syntactic verification to stronger producer, object, ref, tag, and document
checks.

### Corrected

- Every source-ZIP entry now records `S_IFREG | 0644` or `S_IFREG | 0755`. The standalone
  verifier rejects missing file-type bits, noncanonical permission bits, DOS attributes, and
  UTF-8 flags that do not match the filename encoding.
- Integrity-critical JSON must use one canonical byte representation: sorted keys, two-space
  indentation, ASCII escapes, and exactly one final LF.

### Added

- Producer preflight resource ceilings and immediate verification of the just-written source
  ZIP before secondary release artifacts are generated.
- History inventory schema 3 with isolated mirror restoration, exact restored-ref parity,
  dynamic SHA-1/SHA-256 object-ID validation, `git fsck --full --strict`, and an annotated
  `v<version>` tag that must peel to the recorded `HEAD`.
- Passive-PDF policy checks for a single revision, the exact archived PDF-1.5 identity, a
  declared PDF-1.5/PDF-1.7 rebuild allowlist, exact geometry, no trailing payload, and no
  encryption, JavaScript, forms, launch actions, rich media, or embedded files.
- New regression tests for ZIP type-bit/UTF-8 drift, canonical JSON drift, lightweight release
  tags, extra history outputs, PDF incremental updates, active content, and duplicate metadata.

### Formal boundary

The recovery and publication checks are stronger, but the mathematical status is unchanged.
`YangMills.KP.RootedChildFactorialCatalanIdentity n` remains an explicit open general Lean
obligation. No local axiom, `sorry`, or finite-computation overclaim is introduced.
