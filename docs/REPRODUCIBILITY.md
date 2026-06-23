# Reproducibility

## Static repository verification

Requirements: Python 3.11 or newer and Git.

```sh
make static
```

This verifies pins, critical Git blobs, active Lean placeholder policy, exact oracle
axiom sets, captured build evidence, theorem manifest, finite-evidence metadata, claim
boundary, cross-surface metadata alignment, optional extracted-source manifest parity,
semantically pinned workflow actions, local Markdown links, text normalization, canonical
JSON bytes, and the passive single-revision PDF structure.

The workflow-specific policy can also be run directly:

```sh
make actions-check
```

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
make package-repackaging
make verify-source-zip
make verify-release
```

The source ZIP uses sorted `ZIP_STORED` entries, normalized timestamps, canonical
filename-dependent UTF-8 flags, and full Unix regular-file modes (`S_IFREG | 0644/0755`). Avoiding Deflate removes zlib-version-dependent output. An
internal `SOURCE-MANIFEST.sha256`, external checksum, SPDX 2.3 SBOM, complete release
`SHA256SUMS`, theorem-manifest digest, finite-evidence digest, and release metadata are cross-checked against the
working source tree by `scripts/verify_release.py`. The verifier then extracts the ZIP
and executes `python scripts/check_repository.py` inside the extracted copy. This catches
omissions that source-parity alone cannot detect, including missing archived Lean
verification logs.

The verifier additionally requires portable canonical paths, rejects case-insensitive and
Windows filename collisions, validates normalized ZIP metadata and the SPDX path/checksum
inventory, and performs manual regular-file extraction. An extracted release can be checked
and repackaged independently:

```sh
python scripts/check_source_manifest.py
make package-determinism
```

This second-generation packaging check prevents a generated manifest or recovery byproduct
from becoming a duplicate or accidental source entry.

In a Git checkout, publication packaging is tracked-only and requires a clean worktree.
Tracked symbolic links or other non-regular paths fail closed, and untracked files are never
included. The independent verifier requires exactly the five declared release outputs as
regular non-symbolic-link files. The SPDX 2.3 file inventory contains canonical SHA-1 and
SHA-256 values plus the package verification code; SHA-256 remains the release trust anchor.

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

The generated `.bundle` retains commit history and refs, while schema-3 JSON records the
exact HEAD/ref inventory and annotated release tag. Verification mirror-clones the bundle
under isolated Git configuration, runs `git fsck --full --strict`, compares every restored
ref exactly, and requires the release tag to peel to `HEAD`. No cross-Git-version
byte-reproducibility claim is made for the bundle. See [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md).

## Tooling runtime matrix

The standard-library tooling is tested on Python 3.11, 3.12, and 3.13. The reference release job uses Python 3.12. Publication-critical Makefile paths use immediate assignment; see `docs/CI_PORTABILITY.md`.


## Standalone archive verification

Run `scripts/verify_source_zip.py` against the original ZIP and its checksum before
extraction. The verifier reads normalized modes from ZIP metadata, so Windows permission
translation cannot create a false failure. Archive file count and expanded size are bounded,
and project metadata is parsed with duplicate-key, non-finite-number, exponent-overflow, and
exponent-underflow rejection. Integrity-critical JSON is also required to use sorted keys,
two-space indentation, ASCII escapes, and one terminal LF.

History inventories use schema 3 and must equal `git bundle list-heads` and the restored
mirror ref set exactly. The bundle must contain an annotated `v<version>` tag bound to HEAD,
pass strict full-object fsck, and remains explicitly non-byte-reproducible across Git versions.
