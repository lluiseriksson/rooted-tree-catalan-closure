# Release checklist

1. Confirm `git status --short` is empty and `master` is up to date. Do not use
   `--allow-dirty` for a publication build.
2. Review `project.json`, `archive/theorem-manifest.json`, `CITATION.cff`,
   `CITATION.bib`, `codemeta.json`, `.zenodo.json`, `RELEASE_NOTES.md`, and `CHANGELOG.md`;
   run `python scripts/check_metadata_consistency.py`.
3. Run `make actions-check`; review every changed action SHA and major-policy update.
4. Run `make finite-check` and inspect any intentional evidence change.
5. Run `make release`; this includes deterministic/repackaged source checks and the full
   passive-PDF inspection.
6. Run `make verify-source-zip`; confirm the producer self-verification, regular-file type
   bits, canonical UTF-8 flags, sidecar, SPDX SBOM, release metadata, and complete
   `SHA256SUMS` all agree.
7. Extract the source ZIP, run `python scripts/check_source_manifest.py`, and run
   `make package-determinism` from that extracted tree.
8. Confirm all integrity-critical JSON is canonical and that the release directory contains
   exactly the five declared regular non-symbolic-link outputs.
9. Dispatch the full Lean replay if Lean code, patch files, pins, or Lean evidence changed.
10. Commit the final clean tree, then create an annotated tag exactly matching
    `v<project.json version>` at that commit. A lightweight tag is not acceptable.
11. From the tagged commit, run `make history-bundle` and `make verify-history`. Confirm
    schema-3 `bundle_heads` equals `git bundle list-heads`, the mirror-restored refs match
    exactly, `git fsck --full --strict` passes, and the release tag peels to `HEAD`.
12. Confirm the tracked manuscript reports the exact title, author, 17 A4 pages and PDF 1.5;
    confirm rebuilt output uses only the declared PDF 1.5/1.7 allowlist, one revision, and no
    encryption, JavaScript, forms, actions, or embedded files.
13. Copy the source and history recovery sets to independent off-site storage.
14. Push the commit and annotated tag; the release workflow publishes and attests both source
    and history artifacts.
15. Confirm GitHub Actions is green, including patch application, paper reconstruction,
    tagged release, and history backup.
16. Confirm the public release ZIP digest matches the locally verified digest.
17. Record any archival DOI only after the release has been deposited.

Never describe finite checks as a general proof, and never describe the artifact as a
closed formal Catalan proof while `RootedChildFactorialCatalanIdentity n` remains open.
