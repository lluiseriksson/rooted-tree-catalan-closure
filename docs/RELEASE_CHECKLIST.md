# Release checklist

1. Confirm `git status --short` is empty and `master` is up to date.
2. Review `project.json`, `archive/theorem-manifest.json`, `CITATION.cff`,
   `codemeta.json`, `.zenodo.json`, and `CHANGELOG.md`.
3. Run `make actions-check`; review every changed action SHA and any major-policy update.
4. Run `make finite-check` and inspect any intentional evidence change.
5. Run `make release`.
6. Confirm `release/*.zip`, checksum, SPDX SBOM, and release metadata verify cleanly.
7. Confirm the release ZIP uses `ZIP_STORED`, normalized timestamps, includes the
   archived Lean verification logs, and passes the extracted-tree self-audit.
8. Dispatch the full Lean replay if Lean code, patch files, pins, or Lean evidence changed.
9. Run `make history-bundle` and `make verify-history`; inspect the recorded HEAD and refs.
10. Copy the source and history recovery sets to independent off-site storage.
11. Confirm GitHub Actions is green, including patch application and paper reconstruction.
12. Create an annotated tag exactly matching `v<project.json version>`.
13. Push the tag; the release workflow publishes and attests both source and history artifacts.
14. Record any archival DOI only after the release has been deposited.

Never describe finite checks as a general proof, and never describe the artifact as a
closed formal Catalan proof while `RootedChildFactorialCatalanIdentity n` remains open.
