# Supply-chain policy

The repository treats workflow code as maintainable automation rather than immutable
scientific evidence. Whole-workflow Git blob hashes are therefore **not** part of the
scientific provenance lock. Instead, every external GitHub Action must satisfy a
semantic policy:

1. the action repository is explicitly allowlisted;
2. the executable reference is a full 40-character commit SHA;
3. a trailing `# vN` comment records the reviewed release line; and
4. a major-version change requires an explicit update to
   `archive/github-actions-policy.json`.

Run the policy audit with:

```sh
make actions-check
```

This design lets Dependabot propose patch-level SHA updates without invalidating the
manuscript, Lean sources, theorem evidence, or other immutable scientific blobs. It
still prevents mutable tags such as `@main` or `@v7` from executing in CI.

The dependency-review workflow remains blocking for high- or critical-severity newly
introduced vulnerabilities. Lower-severity findings remain visible in the action
summary without turning routine action maintenance into a permanent red check.

This policy does not make third-party workflow code intrinsically trustworthy. Every
SHA change remains reviewable, and release workflows retain minimal declared
permissions plus `persist-credentials: false` on checkouts.
