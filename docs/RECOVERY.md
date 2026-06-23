# Repository recovery record

The repository is operationally recovered as a reproducible publication artifact. Its
formal theorem boundary remains conditional and is documented separately.

## Recovery controls

1. Machine-readable version, pins, status, history, theorem manifest, and critical blobs.
2. Local audit of Lean placeholders, local axioms, claim language, evidence logs, finite
   checks, PDF structure, metadata alignment, links, and workflow safety.
3. CI patch application against the immutable upstream commit and comparison with the
   recovered adapter files.
4. Manually dispatched complete Lean replay with pin checks and a machine-readable report.
5. Three exact finite computations of the Catalan tree identity through documented orders.
6. Cross-runtime deterministic stored ZIP with source manifest, external SHA-256, SPDX
   2.3 SBOM, file-level license records, and release metadata.
7. Independent release/source parity verifier, extracted source-tree self-audit, and
   byte-for-byte packaging replay.
8. Tag-driven release workflow with GitHub provenance attestations and publication checklist.
9. Full Git history/ref bundle with a machine-readable inventory, SHA-256 checksums, and
   independent `git bundle verify` validation.
10. Full-SHA GitHub Action pins governed by an allowlisted major-version policy rather
    than brittle whole-workflow blob locks.

## Acceptance gate

```sh
make verify
make verify-release
make history-bundle
make verify-history
```

With TeX installed:

```sh
make release
```

A public or archival release is accepted only after the corresponding GitHub Actions
checks are green and the tag matches the version recorded in `project.json`.

Detailed restoration commands and the recommended off-site artifact set are in
[DISASTER_RECOVERY.md](DISASTER_RECOVERY.md).
