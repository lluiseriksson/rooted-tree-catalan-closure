# Engineering hardening in v1.5.1 through v1.7.0

## Problem found

The v1.5.0 source archive passed its original release verifier, but rebuilding a release from
that extracted archive failed. Outside a Git checkout, the file inventory used a recursive
filesystem walk. It therefore selected the generated `SOURCE-MANIFEST.sha256`, while the ZIP
writer also generated a new manifest at the same path. Python emitted a duplicate-entry
warning and the independent verifier correctly rejected the result.

This distinction matters for recovery: a source release should not only audit after
extraction; it should remain a valid input to the release tooling it contains.

## Changes

### One source inventory policy

`scripts/source_inventory.py` is now the canonical file selector for both Git checkouts and
extracted source trees. It excludes generated manifests, output directories, interpreter and
test caches, and common platform metadata while preserving the archived Lean evidence logs.

### Strict manifest contract

`scripts/release_integrity.py` defines the normalized source-manifest grammar and portable path
policy. A manifest must use lowercase SHA-256 values, two-space separators, canonical sorted
paths, a terminal newline, and names that remain unambiguous on case-insensitive filesystems.

`scripts/check_source_manifest.py` verifies an extracted source tree independently of release
metadata. `scripts/check_repository.py` invokes the same check automatically whenever the
manifest exists, while ordinary Git checkouts without a generated manifest remain valid.

### Safer ZIP handling

The release verifier now validates every entry before extraction and writes regular files
manually into a fresh directory. It rejects traversal, absolute and backslash paths, repeated
or dot components, Windows-reserved names, case collisions, directory entries, compressed
entries, non-normalized modes, unexpected flags, comments, extra fields, and internal
metadata. This makes the portable-release claim executable rather than documentary.

### Metadata parity

`scripts/check_metadata_consistency.py` compares `project.json` with CFF, BibTeX, CodeMeta,
Zenodo, changelog, release notes, and the theorem manifest. It also checks that upstream pins
and the explicit open-proof boundary agree across machine-readable surfaces.

## Regression coverage

The standard-library unit suite now covers:

- second-generation inventory selection;
- valid and invalid portable source paths;
- malformed, unsorted, duplicate, and case-colliding manifests;
- safe ZIP extraction and normalized metadata;
- duplicate SPDX file paths;
- extracted-source checksum drift; and
- citation/formal-boundary metadata drift.

## Scope boundary

These changes improve release engineering, recovery, portability, and auditability. They do
not modify the recovered manuscript, compiled PDF, Lean declarations, finite evidence, oracle
logs, or the unresolved proposition
`YangMills.KP.RootedChildFactorialCatalanIdentity n` for arbitrary `n`.

## v1.6.0: verify the archive, not Windows extraction modes

A source ZIP carries normalized Unix modes, but an ordinary Windows extraction cannot
faithfully represent the executable bit. Treating the extracted filesystem mode as an
integrity signal therefore produces false positives even when the archive bytes and internal
manifest are correct.

Version 1.6.0 adds `scripts/verify_source_zip.py`. It validates the original archive directly:

- one canonical top-level prefix and sorted entries;
- `ZIP_STORED`, normalized timestamps and 0644/0755 mode policy;
- portable names, case-insensitive uniqueness, CRCs, and bounded expanded size;
- strict `project.json` decoding, including duplicate-key rejection;
- exact internal manifest inventory and file checksums; and
- an optional external `.zip.sha256` sidecar whose filename is also authenticated.

Safe extraction still restores modes on POSIX, but deliberately does not treat Windows host
modes as authoritative. The regression suite extracts a valid archive, removes every
executable bit, and confirms that direct archive verification still succeeds.

## v1.6.0: exact Git bundle head parity

The former history inventory recorded refs from the source checkout, while structural
verification only ran `git bundle verify`. Version 1.6.0 records the actual output of
`git bundle list-heads` as schema-2 `bundle_heads` entries and compares it byte-for-byte at
verification time after canonical parsing. This covers `HEAD`, branch and tag object IDs, and
the temporary detached-head recovery ref. Recomputing the JSON checksum is no longer enough
to hide an omitted advertised ref.

## v1.7.0: publication input and output closure

Version 1.7.0 closes the remaining gap between “files visible in a checkout” and “files
authorized for publication.” In a Git checkout, `scripts/source_inventory.py` now asks Git
for tracked files only. The packager additionally requires an empty porcelain status before
a publication build. Untracked credentials or scratch data cannot enter the ZIP, while a
tracked symbolic link, submodule-like non-regular entry, or missing file causes a hard error
instead of a silent omission. The `--allow-dirty` escape hatch is explicitly development-only
and still never packages untracked files.

The output side is closed as well. A canonical `SHA256SUMS` file authenticates the source ZIP,
its one-record sidecar, the SPDX document, and release metadata. Independent verification
requires exactly those four files plus `SHA256SUMS` in the release directory, all as regular
non-symbolic-link files. This prevents stale, redirected, or undeclared artifacts from being
mistaken for one release set.

## v1.7.0: SPDX 2.3 and strict-number completion

Every analyzed SPDX file now carries exactly one canonical SHA-1 checksum plus an additional
SHA-256. The package contains the verification code computed from the sorted file SHA-1
values, while the ZIP and complete output inventory continue to use SHA-256 as their trust
anchor. Producer and verifier implement the calculation independently and compare it with
the source manifest and archive bytes.

Strict JSON decoding now rejects not only `NaN`, infinities, duplicate keys, and exponent
overflow, but also nonzero exponent values that Python would underflow silently to zero.
Portable path validation also rejects Unicode control, formatting, surrogate, and line-
separator categories so invisible directionality or record-breaking characters cannot enter
manifests or ZIP member names.

## v1.7.0: non-destructive platform parity

The PowerShell manuscript entrypoint now mirrors the Makefile contract: it writes and checks
the rebuilt PDF under `build/` and leaves the tracked recovered PDF untouched unless
`-RefreshTrackedPdf` is supplied. `make verify` also includes the independent release verifier,
so the concise documented gate and the expanded command sequence are equivalent.
