# Rooted-tree summation and Catalan closure

[![Artifact CI](https://github.com/lluiseriksson/rooted-tree-catalan-closure/actions/workflows/artifact-ci.yml/badge.svg)](https://github.com/lluiseriksson/rooted-tree-catalan-closure/actions/workflows/artifact-ci.yml)
[![Manual Lean replay](https://github.com/lluiseriksson/rooted-tree-catalan-closure/actions/workflows/full-lean-replay.yml/badge.svg)](https://github.com/lluiseriksson/rooted-tree-catalan-closure/actions/workflows/full-lean-replay.yml)
[![Lean](https://img.shields.io/badge/Lean-4.29.0--rc6-blue)](project.json)
[![Formal status](https://img.shields.io/badge/formal%20status-conditional%20adapter-orange)](lean-patch/CATALAN_PATCH_STATUS.md)

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
| General Lean proof of `RootedChildFactorialCatalanIdentity n` | **Still open in this artifact** |
| Static integrity, patch applicability, packaging, and release verification | Automated |

The exact remaining proposition is:

```lean
YangMills.KP.RootedChildFactorialCatalanIdentity n
```

The downstream theorem takes that proposition as an explicit hypothesis; it is not
introduced as an axiom. The repository therefore does not claim a closed Lean proof of
the general rooted child-factorial Catalan identity.

## Immutable provenance

| Item | Pinned value |
|---|---|
| Upstream repository | `lluiseriksson/THE-ERIKSSON-PROGRAMME` |
| Inspected upstream base | `1d044a353ac2b69ddca732dd851fb0ab4a94d7af` |
| Checked adapter commit | `d668c333db302f9f399374e3c824805a1c4d71da` |
| Lean | `leanprover/lean4:v4.29.0-rc6` |
| Mathlib | `07642720480157414db592fa85b626dafb71355b` |

`project.json` is the machine-readable source of truth. Its `critical_git_blobs` table
protects the manuscript, PDF, Lean modules, patch, and verification logs from silent
replacement or line-ending damage.

## Verify locally

Static integrity audit:

```sh
make static
```

Rebuild the paper and recheck its structure:

```sh
make verify
```

Create and independently verify a deterministic source ZIP, SHA-256 checksum, SPDX 2.3
SBOM, and release metadata:

```sh
make package-determinism
make verify-release
```

A complete local publication gate is:

```sh
make release
```

## Lean replay

The ordinary CI checks that the mailbox patch applies exactly to the immutable upstream
base and that the recovered source copies match the applied result. The full Lean kernel
replay is a manually dispatched workflow because it rebuilds the large pinned upstream
project.

Equivalent local commands:

```sh
git clone https://github.com/lluiseriksson/THE-ERIKSSON-PROGRAMME.git upstream
cd upstream
git checkout 1d044a353ac2b69ddca732dd851fb0ab4a94d7af
git apply ../rooted-tree-catalan-closure/lean-patch/catalan-conditional-adapter.patch
lake exe cache get
lake build YangMillsCore
lake build YangMills.KP.RootedCatalan YangMills.RG.AppendixFHsharpCatalanClosure
lake build YangMills.RG.AppendixFHsharpCatalanSource
lake env lean oracle_check_catalan.lean
```

The archived evidence records a successful 8,235-job build and exactly
`[propext, Classical.choice, Quot.sound]` for the checked adapter endpoints.

## Repository map

- `main.tex` — canonical manuscript source.
- `Rooted_tree_Catalan_closure.pdf` — recovered compiled manuscript.
- `lean-patch/` — conditional Lean adapter, mailbox patch, oracle driver, and evidence.
- `project.json` — version, pins, formal status, and critical Git blobs.
- `scripts/check_repository.py` — local integrity and claim-boundary audit.
- `scripts/package_release.py` — deterministic package, checksum, SBOM, and metadata.
- `scripts/verify_release.py` — independent verification of generated release files.
- `docs/` — claims boundary, provenance, recovery, reproducibility, and release process.

## Scope

The note isolates a finite rooted-tree/second-Ursell mechanism. It does not construct the
model-specific Yang–Mills activity, a continuum limit, Osterwalder–Schrader
reconstruction, or a Yang–Mills mass gap.
