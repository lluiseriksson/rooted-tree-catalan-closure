# Disaster recovery

The project now supports two complementary recovery artifacts:

1. the deterministic source ZIP, which restores the publication tree; and
2. a Git bundle, which restores commit history and refs.

The source ZIP is byte-reproducible for a fixed source tree. A Git bundle is verified by
checksum and `git bundle verify`, but is not claimed to be byte-identical across Git
versions.

## Create recovery artifacts

```sh
make package-determinism
make verify-release
make history-bundle
make verify-history
```

Generated files are placed in `release/` and `history-release/`.

## Restore from the source ZIP

```sh
sha256sum -c rooted-tree-catalan-closure-v1.4.1.zip.sha256
unzip rooted-tree-catalan-closure-v1.4.1.zip
cd rooted-tree-catalan-closure-v1.4.1
python3 scripts/verify_release.py --release-dir /path/to/release-files
python3 scripts/check_repository.py
```

The ZIP includes `SOURCE-MANIFEST.sha256`. Its external `.zip.sha256`, SPDX SBOM,
and release metadata must agree with that internal inventory and with the current source
tree under `scripts/verify_release.py`.

## Restore full Git history

Keep the `.bundle`, `.history.json`, and `.history.SHA256SUMS` files together.

```sh
sha256sum -c rooted-tree-catalan-closure-v1.4.1.history.SHA256SUMS
git bundle verify rooted-tree-catalan-closure-v1.4.1-history.bundle
git clone rooted-tree-catalan-closure-v1.4.1-history.bundle rooted-tree-catalan-closure
cd rooted-tree-catalan-closure
git checkout <head_commit from the history JSON>
```

After restoration, configure a new remote and push all retained refs:

```sh
git remote add origin <new repository URL>
git push origin --all
git push origin --tags
```

## Minimum off-site set

Store these outside GitHub:

- deterministic source ZIP;
- ZIP checksum, external source manifest, SPDX SBOM, release metadata, and SHA256SUMS;
- Git history bundle, history inventory, and history SHA256SUMS;
- compiled manuscript PDF;
- the tag or commit identifier from which the artifacts were produced.

The formal proof boundary remains unchanged by disaster recovery: the general Lean proof
of `RootedChildFactorialCatalanIdentity n` remains open until a clean kernel replay closes
it.
