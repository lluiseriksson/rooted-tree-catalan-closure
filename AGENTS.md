# Agent instructions

1. Preserve the immutable upstream, Lean, Mathlib, and mailbox-patch pins unless the
   change is an explicitly reviewed provenance migration.
2. Do not describe the artifact as a closed Lean proof while
   `YangMills.KP.RootedChildFactorialCatalanIdentity n` remains open.
3. Treat `evidence/finite-catalan-checks.json` as finite computational evidence only.
4. Never introduce `sorry`, `admit`, `sorryAx`, or a project-local axiom.
5. Keep `project.json`, `archive/theorem-manifest.json`, claim-boundary documentation,
   and oracle evidence synchronized with any Lean-facing change.
6. Do not overwrite the tracked recovered PDF during ordinary builds. Use `make paper` or
   `make paper-check`; use `make paper-refresh` only for an intentional archival update.
7. Run `make verify` and `make verify-release` before proposing a release. Run the full
   pinned Lean replay whenever patch files, Lean sources, pins, or recorded Lean evidence
   change.
8. Preserve both recovery layers: the deterministic source ZIP and the independently
   verified Git history bundle. Never claim the Git bundle is byte-reproducible across
   Git implementations.
9. Do not claim a model-specific Yang–Mills activity estimate, continuum construction,
   Osterwalder–Schrader reconstruction, or mass gap from this finite artifact.

## Immutable pins

- Upstream base: `1d044a353ac2b69ddca732dd851fb0ab4a94d7af`
- Mailbox patch commit: `d668c333db302f9f399374e3c824805a1c4d71da`
- Lean: `leanprover/lean4:v4.29.0-rc6`
- Mathlib: `07642720480157414db592fa85b626dafb71355b`

The checked Lean result is a conditional downstream adapter; the general Catalan
identity remains open in this artifact.

## CI source-selection invariant

Do not weaken `TEX := main.tex` or `TRACKED_PDF := Rooted_tree_Catalan_closure.pdf` to `?=`. The audit treats these as release-critical invariants.
