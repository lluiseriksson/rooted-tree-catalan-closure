# Provenance and chain of custody

The recovered repository history is append-only:

- `7a703cd0b43879aa052183407b292692a8118b28` — initial manuscript bundle.
- `a060fc6d92d862a23e3cf65fc8789eb54c26d7df` — checked conditional adapter bundle.
- `f5b8e0519c9da589b284c4b511665636f5c4a427` — recovery hardening v1.2.0.
- `b4801b6d0d000143f7f4c5358833c526552f0a65` — paper-CI dependency repair (`lmodern`).
- `1f2666a7f34f8fed57295e49d4c236f06a22e7cc` — recovery hardening v1.3.0.
- `e50d83f5f2ebd2cce8d470f39dbeba5fa20f4ff6` — CI fix that hard-pins `main.tex` in the Makefile.
- `27c48960e8ae1b1ebfaafee4c210c26a1f2883e4` — released v1.4.1 finite-evidence and replay hardening.

The v1.5.0 improvement bundle applies on top of released commit `27c48960...` without rewriting prior
history. The recovered Lean adapter remains tied to upstream base
`1d044a353ac2b69ddca732dd851fb0ab4a94d7af` and mailbox patch commit
`d668c333db302f9f399374e3c824805a1c4d71da`.

The primary manuscript, PDF, Lean modules, mailbox patch, oracle driver, evidence logs,
finite Catalan evidence, theorem manifest, and release-verification tooling are pinned by
Git blob ID in `project.json`. Workflow files are governed separately by semantic
full-SHA action policy so routine dependency maintenance cannot invalidate scientific
provenance.
`make static` recomputes those object IDs locally. This detects truncation, accidental
line-ending conversion, replacement, or edits that were not accompanied by an explicit
provenance update.

The finite result table is generated deterministically by
`scripts/check_finite_catalan.py`. Its three methods are implemented independently enough
to catch errors in tree enumeration, Prüfer multiplicities, profile counting, or
normalization. It is recorded as computational evidence only and does not alter the Lean
certification boundary.
