# Security and integrity policy

This repository is not an executable network service. Its principal risks are supply-
chain substitution, corrupted release archives, stale or fabricated verification logs,
incorrect provenance, and accidental overstatement of the formal proof boundary.

Report a suspected security or integrity issue privately through GitHub's private
security advisory feature. Include the affected path, commit or release, reproduction
steps, and expected versus observed hashes when relevant.

Supported versions:

| Version | Supported |
|---|---|
| 1.3.x | Yes |
| Earlier recovery bundles | Upgrade recommended |

Before trusting a release, run `make verify-release` and compare its published SHA-256
checksum. Lean claims additionally require the pinned full replay described in
`docs/REPRODUCIBILITY.md`.
