# CI and tooling portability

The recovery tooling intentionally depends only on the Python standard library. GitHub
Actions runs the unit suite on Python 3.11, 3.12, and 3.13, while the publication gate
uses Python 3.12 as its reference runtime.

The manuscript source and tracked PDF names are deliberately hard-pinned in the
Makefile:

```make
TEX := main.tex
TRACKED_PDF := Rooted_tree_Catalan_closure.pdf
```

This prevents inherited environment variables such as `TEX=tex` from changing the file
compiled by CI. The repository audit rejects a return to conditional `?=` assignment for
these two publication-critical paths.

The matrix job performs the standard-library unit tests and a reduced finite Catalan
smoke check. The reference job additionally runs the complete finite evidence, source
package determinism, standalone permission-independent ZIP verification, and independent
release verification.


On Windows, extracted filesystem modes are not used as proof of the executable policy. The
source ZIP verifier checks the normalized 0644/0755 attributes in the archive itself; safe
extraction only reapplies those modes on POSIX. This keeps validation consistent across
Python 3.11–3.13 and across host permission models.
