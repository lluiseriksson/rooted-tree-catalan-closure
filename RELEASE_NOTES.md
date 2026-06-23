# Release notes

## v1.5.0 self-auditing source and workflow supply-chain hardening

This release fixes two maintenance gaps found after the successful v1.4.1 publication.
The action-update pull requests changed only workflow dependencies, but the repository
auditor treated entire workflow files as immutable scientific blobs. In addition, the
source packager excluded all `.log` files, including the archived Lean build and oracle
evidence required by the repository audit.

### Corrected

- Workflow safety is now checked semantically instead of by whole-file Git blob hashes.
- Every external action is allowlisted, pinned to a full 40-character commit SHA, and
  annotated with its reviewed major release line.
- GitHub Actions dependencies are grouped into one monthly Dependabot update.
- Dependency review retries snapshot warnings and blocks newly introduced high or
  critical vulnerabilities.
- The deterministic source ZIP includes the archived Lean build and oracle logs.
- `scripts/verify_release.py` extracts the source ZIP and runs the repository audit from
  that clean extracted tree.

### Preserved

- Manuscript, PDF, Lean adapter, upstream pins, theorem statements, finite evidence, and
  the explicit conditional proof boundary are unchanged.
- `YangMills.KP.RootedChildFactorialCatalanIdentity n` remains open for arbitrary `n`.

### Recommended publication gate

```sh
make ci
make package-determinism
make verify-release
make history-bundle
make verify-history
```
