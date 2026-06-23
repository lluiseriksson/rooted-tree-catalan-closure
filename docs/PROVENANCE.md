# Provenance and chain of custody

The recovered repository history is append-only:

- `7a703cd0b43879aa052183407b292692a8118b28` — initial manuscript bundle.
- `a060fc6d92d862a23e3cf65fc8789eb54c26d7df` — checked conditional adapter bundle.
- `f5b8e0519c9da589b284c4b511665636f5c4a427` — recovery hardening v1.2.0.

The v1.3.0 hardening applies on top of the third commit without rewriting prior history.
The recovered Lean adapter is tied to upstream base
`1d044a353ac2b69ddca732dd851fb0ab4a94d7af` and mailbox patch commit
`d668c333db302f9f399374e3c824805a1c4d71da`. The primary manuscript, PDF, Lean
modules, mailbox patch, oracle driver, and evidence logs are pinned by Git blob ID in
`project.json`.

`make static` recomputes those object IDs locally. This detects truncation, accidental
line-ending conversion, replacement, or edits that were not accompanied by an explicit
provenance update.
