# Engineering hardening in v1.5.1 and v1.6.0

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
