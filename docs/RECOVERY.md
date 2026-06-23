# Repository recovery record

The repository is operationally recovered as a reproducible publication artifact. Its
formal theorem boundary remains conditional and is documented separately.

## Recovery controls

1. Machine-readable version, pins, status, history, and critical Git blobs.
2. Local audit of active Lean placeholders, local axioms, claim language, evidence logs,
   PDF structure, metadata alignment, and workflow safety.
3. CI patch application against the immutable upstream commit.
4. Manually dispatched complete Lean replay in the pinned environment.
5. Deterministic ZIP creation with internal source manifest, external SHA-256, SPDX 2.3
   SBOM, and release metadata.
6. Independent release verifier and byte-for-byte packaging replay.
7. Tag-driven release workflow and publication checklist.

## Acceptance gate

```sh
make static
make package-determinism
make verify-release
```

With TeX installed:

```sh
make release
```

A public or archival release is accepted only after the corresponding GitHub Actions
checks are green and the tag matches the version recorded in `project.json`.
