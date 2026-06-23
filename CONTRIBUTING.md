# Contributing

Changes are welcome when they preserve the artifact's mathematical, provenance, and
reproducibility boundary.

Before proposing a change, run:

```sh
make static
make package-determinism
make verify-release
```

Run `make verify` when TeX is available. Changes to `lean-patch/` must additionally pass
the manually dispatched full Lean replay.

## Lean changes

A Lean change must:

1. contain no `sorry`, `admit`, `sorryAx`, or project-local axiom;
2. keep assumptions explicit in theorem statements;
3. update the oracle driver and captured evidence;
4. update `project.json`, the status page, manifest, and claims boundary together;
5. identify the exact upstream, Lean, and Mathlib revisions used for verification.

Do not rename the conditional identity as a proved theorem until the general bijection
has passed a clean kernel build.

## Manuscript changes

`main.tex` is canonical. Rebuild and visually inspect the PDF, then intentionally update
the corresponding critical Git blobs in `project.json` in the same change.

## Pin and release changes

Dependency pins must change in a dedicated, fully replayed commit. A release tag must
exactly equal `v` followed by the version in `project.json` and `CITATION.cff`.
