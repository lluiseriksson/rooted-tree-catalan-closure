# Recovery log

## 2026-06-23 recovery hardening

The repository was hardened from a paper-plus-patch bundle into a more complete archival
artifact.  The recovery adds:

- machine-readable `project.json`;
- explicit claims boundary;
- reproducibility and release packaging scripts;
- GitHub Actions workflow for audit, packaging, and optional paper build;
- citation and licensing metadata;
- security policy and changelog;
- deterministic source ZIP creation.

## Integrity anchors

The recovery keeps the existing Lean boundary intact.  The checked adapter remains
conditional on `YangMills.KP.RootedChildFactorialCatalanIdentity n`, and the repository
continues to state that the general Catalan bijection is not yet closed.

The recovery baseline before this hardening was the public `master` branch containing
commit `a060fc6d92d862a23e3cf65fc8789eb54c26d7df`.
