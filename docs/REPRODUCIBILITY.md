# Reproducibility

## Static repository verification

Requirements: Python 3.11 or newer and Git.

```sh
make static
```

This verifies pins, critical Git blobs, Lean placeholder policy, exact oracle axiom
sets, build evidence, claim boundary, metadata, workflows, text normalization, and PDF
structure.

## Manuscript

With a TeX distribution:

```sh
make verify
```

The audit accepts a rebuilt PDF structurally because TeX/PDF metadata can prevent a
byte-identical rebuild. The canonical tracked PDF remains protected by its Git blob ID.

## Deterministic release

```sh
make package-determinism
make verify-release
```

The release ZIP uses normalized timestamps, path order, UTF-8 names, and permissions. An
internal `SOURCE-MANIFEST.sha256`, external checksum, SPDX 2.3 SBOM, and release metadata
are cross-checked by `scripts/verify_release.py`.

## Full Lean replay

Dispatch `.github/workflows/full-lean-replay.yml` or follow the pinned commands in the
README. This is the authoritative clean-kernel replay for the checked conditional adapter.
