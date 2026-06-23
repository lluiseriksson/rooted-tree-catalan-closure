# Release checklist

1. Confirm `git status --short` is empty and `master` is up to date.
2. Review `project.json`, `CITATION.cff`, `codemeta.json`, `.zenodo.json`, and changelog.
3. Run `make release`.
4. Confirm `release/*.zip`, checksum, SPDX SBOM, and release metadata verify cleanly.
5. Dispatch the full Lean replay if Lean or patch evidence changed.
6. Confirm GitHub Actions is green.
7. Create an annotated tag exactly matching `v<project.json version>`.
8. Push the tag; the release workflow publishes the verified artifacts.
9. Record any archival DOI only after the release has been deposited.

Never describe the artifact as a closed formal Catalan proof while the explicit
`RootedChildFactorialCatalanIdentity n` obligation remains open.
