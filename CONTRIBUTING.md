# Contributing

Contributions are welcome when they preserve the artifact's provenance, reproducibility,
and formal-claim boundary.

## Required checks

For documentation, metadata, evidence, or tooling changes:

```sh
make ci
make package-determinism
make package-repackaging
make verify-source-zip
make verify-release
make history-bundle
make verify-history
```

Run publication packaging from a clean Git worktree. The release inventory is tracked-file
only; `--allow-dirty` is for local development diagnostics and must not be used for a public
or archival release. Tracked symbolic links, missing files, and other non-regular entries are
release errors rather than silently omitted inputs.

For TeX changes, also run:

```sh
make paper-check
```

Use `make paper-refresh` only when intentionally replacing the tracked recovered PDF;
update its critical Git blob and provenance record in the same change.
PowerShell users should run `./build.ps1`; use `-RefreshTrackedPdf` only for the same explicit
archival replacement.

## Finite evidence changes

`scripts/check_finite_catalan.py` and `evidence/finite-catalan-checks.json` form one
review unit. Regenerate with `make finite-refresh`, inspect the complete diff, and keep
the status text explicit that finite computation is not the general Lean proof.

## Lean or patch changes

A Lean-facing change must include:

1. a clean proof with no `sorry`, `admit`, `sorryAx`, or project-local axiom;
2. updated source copies and mailbox patch;
3. an updated oracle driver and exact axiom report;
4. updated `archive/theorem-manifest.json`, claim-boundary documentation, and pins;
5. a clean full replay in the immutable upstream environment.

Do not replace an explicit hypothesis with a hidden axiom. If the general
`RootedChildFactorialCatalanIdentity n` is completed, update every conditional-status
surface atomically.

## Dependencies and workflows

GitHub Actions changes must keep permissions minimal, disable persisted checkout
credentials, use immutable repository/toolchain pins where the project provides them,
and preserve tag-only guards on publication and attestation steps.

## Recovery tooling changes

Changes to history backup code must preserve the explicit distinction between the
byte-deterministic source ZIP and the checksum/structure-verified Git bundle. Run the
history integration test and confirm a clone from the generated bundle retains earlier
commits and tags.

## Publication-critical Make variables

Keep `TEX := main.tex` and `TRACKED_PDF := Rooted_tree_Catalan_closure.pdf` as immediate assignments. Conditional assignment permits runner environment variables to select the wrong manuscript source.


## Release and metadata hardening

Run the metadata parity checker after changing any version, date, repository URL, citation,
release note, upstream pin, theorem status, or formal-boundary field:

```sh
python scripts/check_metadata_consistency.py
```

When testing from an extracted source release, verify the generated inventory before any
other operation and then prove that the tree can be packaged again:

```sh
python scripts/check_source_manifest.py
make package-determinism
make verify-release
```

Release ZIP changes must preserve canonical POSIX paths, cross-platform filename safety,
case-insensitive uniqueness, normalized metadata, safe manual extraction, and exact manifest,
SBOM, and working-tree parity. Add a regression test for every newly accepted or rejected
archive form.

The release directory must contain exactly the five declared regular-file outputs. Preserve
the complete `SHA256SUMS`, the one-record ZIP sidecar, canonical SPDX 2.3 SHA-1/SHA-256 file
checksums, and the package verification code. SHA-256 remains the release trust anchor.


## Permission-independent archive verification

Do not infer source-archive validity from modes observed after extraction. Windows does not
faithfully reproduce Unix executable bits. Validate the original ZIP with
`scripts/verify_source_zip.py`; the normalized modes inside the ZIP are authoritative.
Integrity-critical JSON must be loaded through `scripts/strict_json.py` so duplicate keys and
non-finite values cannot be silently normalized. History changes must preserve exact parity
between `bundle_heads` and `git bundle list-heads`.

## Canonical metadata, ZIP, PDF, and history contracts

Integrity-critical JSON must be written with `strict_json.canonical_dumps` and read with
`load_canonical`/`loads_canonical`. A semantically equivalent reformat is an integrity error,
not a harmless normalization.

Source ZIP entries must use full Unix regular-file modes (`S_IFREG | 0644/0755`) and the UTF-8
flag only when the filename cannot be represented as ASCII. The packager must keep its
producer-side resource preflight and immediate standalone verification.

Run `make paper-check` with Poppler tools installed. The tracked archival PDF must retain
its exact 17-page A4/PDF-1.5 identity. Rebuilds may use only the declared PDF-1.5/PDF-1.7
allowlist, with one revision and no active or embedded content.

Create the annotated `v<version>` tag before running the history release. History tooling
changes must preserve isolated mirror restoration, exact restored-ref parity,
`git fsck --full --strict`, and proof that the annotated tag peels to `HEAD`.
