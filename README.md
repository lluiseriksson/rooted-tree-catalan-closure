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
| Manuscript source and compiled PDF | Recovered and integrity-pinned |
| Conditional Lean adapter | Checked in the archived pinned environment |
| Square-root Catalan closure | Checked in Lean |
| Appendix-F marked-root adapter | Checked, conditional on the Catalan identity |
| Exact finite tree identity, `0 ≤ n ≤ 8` | Recomputed by three integer-only methods |
| General Lean proof of `RootedChildFactorialCatalanIdentity n` | **Still open in this artifact** |
| Static integrity, patch applicability, packaging, and release verification | Automated |
| Full Git history and refs | Recoverable through a verified Git bundle |

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
and theorem manifest from silent replacement or line-ending damage. The declaration
status is mirrored in [archive/theorem-manifest.json](archive/theorem-manifest.json).

## Verify locally

The non-TeX CI gate is:

```sh
make ci
make package-determinism
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

Create a deterministic source ZIP, SHA-256 checksum, SPDX 2.3 SBOM, and release metadata:

```sh
make package
```

The source ZIP uses uncompressed, normalized entries (`ZIP_STORED`) so its bytes do not
depend on a particular zlib version.

Preserve and verify the complete commit graph and refs separately:

```sh
make history-bundle
make verify-history
```

`make recovery` builds and verifies both recovery layers. The Git bundle is checksummed
and checked with `git bundle verify`; unlike the source ZIP, it is not claimed to be
byte-identical across Git versions. See
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
- `evidence/` — deterministic exact finite checks and their scope statement.
- `project.json` — version, pins, formal status, critical blobs, and release policy.
- `scripts/check_repository.py` — local integrity and claim-boundary audit.
- `scripts/package_release.py` — deterministic package, checksum, SBOM, and metadata.
- `scripts/verify_release.py` — independent release/source parity verification.
- `scripts/create_history_bundle.py` — complete Git history/ref recovery bundle.
- `schema/project.schema.json` — machine-readable metadata contract.
- `docs/` — claims boundary, provenance, recovery, reproducibility, and proof roadmap.

## Scope

The note isolates a finite rooted-tree/second-Ursell mechanism. It does not construct the
model-specific Yang–Mills activity, a continuum limit, Osterwalder–Schrader
reconstruction, or a Yang–Mills mass gap.
