# Reproducibility

## Paper

```sh
make paper
```

or, when Tectonic is installed:

```sh
make tectonic
```

## Static artifact audit

```sh
make audit
```

The audit checks for required files, confirms that the Lean adapter remains explicitly
conditional, verifies the oracle log boundary, and guards against accidental claims that
the exact Catalan identity or mass-gap-level conclusions have already been proved.

## Source package

```sh
make package
```

This creates `release/rooted-tree-catalan-closure-source.zip` and a matching SHA-256
file from a deterministic file list.
