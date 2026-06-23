# Rooted-tree summation and Catalan closure

[![Artifact CI](https://github.com/lluiseriksson/rooted-tree-catalan-closure/actions/workflows/artifact-ci.yml/badge.svg)](https://github.com/lluiseriksson/rooted-tree-catalan-closure/actions/workflows/artifact-ci.yml)
[![Manual Lean replay](https://github.com/lluiseriksson/rooted-tree-catalan-closure/actions/workflows/full-lean-replay.yml/badge.svg)](https://github.com/lluiseriksson/rooted-tree-catalan-closure/actions/workflows/full-lean-replay.yml)
[![Lean](https://img.shields.io/badge/Lean-4.29.0--rc6-blue)](project.json)
[![Formal status](https://img.shields.io/badge/formal%20status-conditional%20adapter-orange)](lean-patch/CATALAN_PATCH_STATUS.md)
[![Finite evidence](https://img.shields.io/badge/exact%20finite%20checks-n%20%E2%89%A4%208-success)](evidence/finite-catalan-checks.json)

This repository is the recovered publication artifact for **Rooted-tree summation and
Catalan closure for polymer cluster expansions with holes**. It contains the canonical
LaTeX manuscript, compiled PDF, exact Lean 4 adapter patch, captured verification
evidence, immutable provenance records, CI, and deterministic release tooling.

## Recovery and formal status

Repository recovery and theorem completeness are separate questions:

| Component | Status |
|---|---|
| Manuscript source and compiled PDF | Recovered, integrity-pinned, and checked as a passive single-revision 17-page A4 PDF |
| Conditional Lean adapter | Checked in the archived pinned environment |
| Square-root Catalan closure | Checked in Lean |
| Appendix-F marked-root adapter | Checked, conditional on the Catalan identity |
| Exact finite tree identity, `0 ≤ n ≤ 8` | Recomputed by three integer-only methods |
| General Lean proof of `RootedChildFactorialCatalanIdentity n` | **Still open in this artifact** |
| Static integrity, patch applicability, packaging, and release verification | Automated |
| Source ZIP self-audit and archived Lean evidence | Built from tracked files in a clean tree; verified directly, after extraction, and after second-generation repackaging |
| Workflow supply chain | Allowlisted actions pinned to full commit SHAs |
| Full Git history and refs | Recoverable through a mirror-restored, strict-fsck Git bundle bound to the annotated release tag |

The exact remaining proposition is:

```lean
YangMills.KP.RootedChildFactorialCatalanIdentity n
```

The downstream theorem takes that proposition as an explicit hypothesis; it is not
introduced as an axiom. Finite computation is useful regression evidence, but it does
not turn the conditional adapter into a general Lean proof.

## New independent finite evidence

`scripts/check_finite_catalan.py` verifies the exact integer identity

```text
Σ_T ∏_v c_T(v)! = n! · Catalan(n)
```

by three routes:

1. exhaustive Prüfer words through `n = 8`;
2. exhaustive complete-graph edge subsets that are trees through `n = 7`; and
3. exhaustive Prüfer occurrence profiles through `n = 8`.

Run it with:

```sh
make finite-check
```

The deterministic result table is in [evidence/finite-catalan-checks.json](evidence/finite-catalan-checks.json).
The resulting Prüfer-profile reduction and a narrow Lean closure plan are documented in
[docs/PRUFER_PROFILE_REDUCTION.md](docs/PRUFER_PROFILE_REDUCTION.md).

## Immutable provenance

| Item | Pinned value |
|---|---|
| Upstream repository | `lluiseriksson/THE-ERIKSSON-PROGRAMME` |
| Inspected upstream base | `1d044a353ac2b69ddca732dd851fb0ab4a94d7af` |
| Checked adapter commit | `d668c333db302f9f399374e3c824805a1c4d71da` |
| Lean | `leanprover/lean4:v4.29.0-rc6` |
| Mathlib | `07642720480157414db592fa85b626dafb71355b` |

[project.json](project.json) is the machine-readable source of truth. Its
`critical_git_blobs` table protects the manuscript, PDF, Lean modules, patch, evidence,
and theorem manifest from silent replacement or line-ending damage. Workflow files are
not frozen as scientific blobs; they are governed semantically by full-SHA action pins
and an allowlisted major-version policy. See
[docs/SUPPLY_CHAIN.md](docs/SUPPLY_CHAIN.md). The declaration status is mirrored in
[archive/theorem-manifest.json](archive/theorem-manifest.json).

## Verify locally

The non-TeX CI gate is:

```sh
make ci
make package-determinism
make package-repackaging
make verify-source-zip
make verify-release
```

A concise equivalent is:

```sh
make verify
```

With a TeX distribution installed, rebuild and inspect the manuscript without changing
the tracked recovered PDF:

```sh
make paper-check
```

`make paper` writes `build/Rooted_tree_Catalan_closure.pdf`. Replacing the tracked PDF
requires the explicit `make paper-refresh` target.

On PowerShell, `./build.ps1` follows the same non-destructive policy. Use
`./build.ps1 -RequirePdfTools` requests the full Poppler inspection suite; use
`-RefreshTrackedPdf` only for an intentional archival replacement.

Create the five canonical release outputs: deterministic source ZIP, ZIP sidecar,
SPDX 2.3 SBOM, release metadata, and complete release checksums:

```sh
make package
```

Publication packaging refuses a dirty Git worktree and inventories tracked regular files
only. Untracked or ignored files are never packaged; tracked symbolic links and missing or
non-regular paths fail closed. `--allow-dirty` exists only for deliberate development builds.
The generated `SHA256SUMS` covers the ZIP, sidecar, SBOM, and metadata, while the independent
verifier requires exactly the five declared regular-file outputs.

The source ZIP uses uncompressed, normalized entries (`ZIP_STORED`) so its bytes do not
depend on a particular zlib version. Every entry carries an explicit Unix regular-file type
bit, canonical `0644`/`0755` permissions, and a UTF-8 flag only when its filename needs one.
The producer applies the same resource ceilings as the verifier and verifies the completed
ZIP before emitting the remaining release metadata. It includes the archived Lean build/oracle logs, is
extracted into a clean directory, and runs its own repository audit during
`make verify-release`.

### Direct, extracted, and second-generation verification

The source ZIP is verified in three independent forms. Before extraction, verify its bytes
and canonical archive metadata directly:

```sh
python scripts/verify_source_zip.py \
  release/rooted-tree-catalan-closure-v1.8.0.zip \
  --checksum release/rooted-tree-catalan-closure-v1.8.0.zip.sha256
```

This check treats ZIP metadata as authoritative and deliberately does not trust executable
bits produced by a Windows extractor. It also rejects traversal, case collisions, unsafe
portable names, noncanonical JSON bytes, duplicate JSON keys, non-finite JSON numbers, CRC
failures, incorrect regular-file metadata or UTF-8 flags, and implausible archive sizes. After extraction, verify the complete internal inventory with:

```sh
python scripts/check_source_manifest.py
```

The same extracted tree can run `make package-determinism`, `make package-repackaging`, and
`make verify-release` without re-adding the generated manifest. Cross-surface release and
theorem metadata can be checked with `python scripts/check_metadata_consistency.py`. See
[docs/ENGINEERING_HARDENING.md](docs/ENGINEERING_HARDENING.md) for the regression record.

The SPDX 2.3 document records the canonical SHA-1 required for each analyzed file, an
additional SHA-256, and the package verification code. SHA-256 remains the trust anchor for
the source archive and every release output; SHA-1 is used only for SPDX interoperability.

Preserve and verify the complete commit graph and refs separately:

```sh
make history-bundle
make verify-history
```

`make recovery` builds and verifies both recovery layers. The Git bundle is checksummed,
checked with `git bundle verify`, mirror-restored under an isolated Git configuration, checked
with `git fsck --full --strict`, compared with its exact restored ref set, and required to
contain an annotated `v<version>` tag that peels to `HEAD`; unlike the source ZIP, it is not
claimed to be byte-identical across Git versions. See
[docs/DISASTER_RECOVERY.md](docs/DISASTER_RECOVERY.md).

## CI portability

The pure-Python recovery tooling is exercised on Python 3.11, 3.12, and 3.13.
The Makefile uses immediate assignments for `TEX := main.tex` and the tracked PDF name,
preventing runner environment variables from selecting a different manuscript source.
See [docs/CI_PORTABILITY.md](docs/CI_PORTABILITY.md).

## Lean replay

Ordinary CI checks that the mailbox patch applies exactly to the immutable upstream base
and that recovered source copies match the applied result. The full Lean kernel replay
is manually dispatched because it rebuilds the large pinned upstream project. It now
verifies upstream pins and emits a machine-readable replay report.

Local patch application only:

```sh
make upstream-replay
```

Full local replay:

```sh
bash scripts/bootstrap_upstream_patch.sh --clean --build
```

A PowerShell equivalent is available as `scripts/bootstrap_upstream_patch.ps1`.

The archived evidence records a successful 8,235-job build and exactly
`[propext, Classical.choice, Quot.sound]` for the checked adapter endpoints.

## Repository map

- `main.tex` — canonical manuscript source.
- `Rooted_tree_Catalan_closure.pdf` — recovered compiled manuscript.
- `lean-patch/` — conditional Lean adapter, mailbox patch, oracle driver, and evidence.
- `archive/theorem-manifest.json` — machine-readable theorem status and evidence map.
- `archive/github-actions-policy.json` — reviewed workflow action allowlist and major lines.
- `evidence/` — deterministic exact finite checks and their scope statement.
- `project.json` — version, pins, formal status, critical blobs, and release policy.
- `scripts/check_repository.py` — local integrity and claim-boundary audit.
- `scripts/check_actions_pins.py` — semantic full-SHA workflow supply-chain audit.
- `scripts/package_release.py` — deterministic package, checksum, SBOM, and metadata.
- `scripts/source_inventory.py` — shared Git/no-Git source selection policy.
- `scripts/release_integrity.py` — portable path, manifest, ZIP, and extraction invariants.
- `scripts/check_source_manifest.py` — extracted-source tree verification.
- `scripts/check_metadata_consistency.py` — citation/release/theorem metadata parity.
- `scripts/strict_json.py` — strict parsing and canonical JSON byte encoding.
- `scripts/verify_source_zip.py` — standalone permission-independent ZIP verification.
- `scripts/verify_release.py` — independent release/source parity verification.
- `scripts/create_history_bundle.py` — complete Git history/ref recovery bundle.
- `scripts/history_integrity.py` — mirror restoration, exact-ref, tag, and strict-object checks.
- `scripts/check_pdf.py` — structural and Poppler-backed passive manuscript inspection.
- `schema/project.schema.json` — machine-readable metadata contract.
- `build.ps1` — non-destructive PowerShell manuscript build and inspection entrypoint.
- `docs/` — claims boundary, provenance, recovery, reproducibility, and proof roadmap.

## Scope

The note isolates a finite rooted-tree/second-Ursell mechanism. It does not construct the
model-specific Yang–Mills activity, a continuum limit, Osterwalder–Schrader
reconstruction, or a Yang–Mills mass gap.
