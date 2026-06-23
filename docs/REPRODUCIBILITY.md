# Reproducibility

## Static repository verification

Requirements: Python 3.11 or newer and Git.

```sh
make static
```

This verifies pins, critical Git blobs, active Lean placeholder policy, exact oracle
axiom sets, captured build evidence, theorem manifest, finite-evidence metadata, claim
boundary, metadata alignment, workflows, local Markdown links, text normalization, and
PDF structure.

## Exact finite Catalan evidence

```sh
make finite-check
```

The checker uses integer arithmetic only. It exhausts Prüfer words through `n = 8`,
complete-graph edge subsets that are spanning trees through `n = 7`, and Prüfer
occurrence profiles through `n = 8`. It compares all methods with `n! · Catalan(n)` and
with the tracked deterministic JSON. This is finite evidence, not the missing general
Lean proof.

Regenerate the tracked table only after intentional review:

```sh
make finite-refresh
```

## Manuscript

With a TeX distribution:

```sh
make paper-check
```

The rebuilt PDF is written under `build/`; the tracked recovered PDF is not modified.
Use `make paper-refresh` only when intentionally replacing the archival PDF and updating
its provenance record.

## Deterministic release

```sh
make package-determinism
make verify-release
```

The source ZIP uses sorted `ZIP_STORED` entries, normalized timestamps, UTF-8 names, and
normalized permissions. Avoiding Deflate removes zlib-version-dependent output. An
internal `SOURCE-MANIFEST.sha256`, external checksum, SPDX 2.3 SBOM, theorem-manifest
digest, finite-evidence digest, and release metadata are cross-checked against the
working source tree by `scripts/verify_release.py`.

## Full Lean replay

Dispatch `.github/workflows/full-lean-replay.yml` or run:

```sh
bash scripts/bootstrap_upstream_patch.sh --clean --build
```

The replay verifies the upstream commit, Lean toolchain, Mathlib pin, patch application,
build result, and exact theorem axiom reports, then emits `replay-report.json`.

## Full-history disaster recovery

```sh
make history-bundle
make verify-history
```

The generated `.bundle` retains commit history and refs, while the companion JSON records
the exact HEAD and ref inventory. SHA-256 protects the bytes and `git bundle verify`
checks structural usability. No cross-Git-version byte-reproducibility claim is made for
the bundle. See [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md).

## Tooling runtime matrix

The standard-library tooling is tested on Python 3.11, 3.12, and 3.13. The reference release job uses Python 3.12. Publication-critical Makefile paths use immediate assignment; see `docs/CI_PORTABILITY.md`.
