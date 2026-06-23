# Release checklist

1. Confirm `git status --short` is empty and `master` is up to date.
2. Review `project.json`, `archive/theorem-manifest.json`, `CITATION.cff`,
   `CITATION.bib`, `codemeta.json`, `.zenodo.json`, `RELEASE_NOTES.md`, and `CHANGELOG.md`;
   run `python scripts/check_metadata_consistency.py`.
3. Run `make actions-check`; review every changed action SHA and any major-policy update.
4. Run `make finite-check` and inspect any intentional evidence change.
5. Run `make release`.
6. Run `make verify-source-zip`; confirm the ZIP, checksum, SPDX SBOM, and release metadata verify cleanly.
7. Confirm the release ZIP uses `ZIP_STORED`, normalized timestamps and permissions,
   canonical portable paths, includes the archived Lean verification logs, and passes the
   extracted-tree self-audit.
8. Extract the source ZIP, run `python scripts/check_source_manifest.py`, then run
   `make package-determinism` from that extracted tree to verify second-generation recovery.
9. Dispatch the full Lean replay if Lean code, patch files, pins, or Lean evidence changed.
10. Run `make history-bundle` and `make verify-history`; confirm schema-2 `bundle_heads` exactly matches `git bundle list-heads`.
11. Copy the source and history recovery sets to independent off-site storage.
12. Confirm GitHub Actions is green, including patch application and paper reconstruction.
13. Create an annotated tag exactly matching `v<project.json version>`.
14. Push the tag; the release workflow publishes and attests both source and history artifacts.
15. Record any archival DOI only after the release has been deposited.

Never describe finite checks as a general proof, and never describe the artifact as a
closed formal Catalan proof while `RootedChildFactorialCatalanIdentity n` remains open.
