# Release notes

## v1.2.0 recovery hardening

This release turns the existing rooted-tree Catalan closure bundle into a more complete
archival artifact while preserving the mathematical honesty boundary.

### Added

- `project.json` with provenance, exact status, and unresolved proof obligation.
- Static audit and deterministic source packaging scripts.
- GitHub Actions workflow for audit, package, and paper build.
- Claims boundary, recovery log, reproducibility notes, security policy, citation file,
  changelog, and documentation license.

### Preserved

- The manuscript and checked conditional Lean adapter.
- The explicit statement that `RootedChildFactorialCatalanIdentity n` remains to be
  proved for every `n`.

### Not claimed

This release does not claim a closed formal proof of the exact Catalan identity, a
Yang--Mills activity estimate, continuum construction, OS reconstruction, or mass gap.
