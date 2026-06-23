# Release checklist

1. Confirm `git status --short` is empty and `master` is up to date.
2. Review `project.json`, `archive/theorem-manifest.json`, `CITATION.cff`,
   `codemeta.json`, `.zenodo.json`, and `CHANGELOG.md`.
3. Run `make finite-check` and inspect any intentional evidence change.
4. Run `make release`.
5. Confirm `release/*.zip`, checksum, SPDX SBOM, and release metadata verify cleanly.
6. Confirm the release ZIP uses `ZIP_STORED`, normalized timestamps, and matches the
   current source tree under `scripts/verify_release.py`.
7. Dispatch the full Lean replay if Lean code, patch files, pins, or Lean evidence changed.
8. Run `make history-bundle` and `make verify-history`; inspect the recorded HEAD and refs.
9. Copy the source and history recovery sets to independent off-site storage.
10. Confirm GitHub Actions is green, including patch application and paper reconstruction.
11. Create an annotated tag exactly matching `v<project.json version>`.
12. Push the tag; the release workflow publishes and attests both source and history artifacts.
13. Record any archival DOI only after the release has been deposited.

Never describe finite checks as a general proof, and never describe the artifact as a
closed formal Catalan proof while `RootedChildFactorialCatalanIdentity n` remains open.
