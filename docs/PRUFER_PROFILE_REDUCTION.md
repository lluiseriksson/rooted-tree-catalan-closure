# Prüfer-profile reduction of the remaining Catalan identity

The remaining Lean obligation is

```lean
YangMills.KP.RootedChildFactorialCatalanIdentity n
```

for every natural number `n`. The manuscript proves the identity mathematically. This
page records a particularly narrow route for the missing formal proof and separates it
from the already checked conditional downstream adapter. The general Lean identity
remains open; this reduction is not a proof inside Lean.

## Exact reduction

Let `T` be a labelled tree on `{0, …, n}`, rooted at `0`, and let its Prüfer word have
multiplicity profile

```text
a_v = number of occurrences of v in the Prüfer word.
```

The Prüfer word has length `n - 1`. The degree formula gives

```text
deg_T(v) = a_v + 1.
```

After orienting the tree away from the root, the rooted child counts are therefore

```text
c_T(0) = a_0 + 1,
c_T(v) = a_v       for v ≠ 0.
```

Hence

```text
∏_v c_T(v)! = (a_0 + 1)! ∏_{v ≠ 0} a_v!.
```

For a fixed profile `a` with `Σ_v a_v = n - 1`, the number of Prüfer words with that
profile is the multinomial coefficient

```text
(n - 1)! / ∏_v a_v!.
```

Multiplying by the tree weight cancels every profile factorial except the extra root
factor:

```text
(number of words of profile a) · (tree weight)
  = (n - 1)! · (a_0 + 1).
```

Thus the tree sum reduces to a weak-composition sum:

```text
Σ_T ∏_v c_T(v)!
  = (n - 1)! · Σ_{a_0+···+a_n=n-1} (a_0 + 1).
```

By symmetry of weak compositions,

```text
Σ_a (a_0 + 1) = n · Catalan(n),
```

and therefore

```text
Σ_T ∏_v c_T(v)! = n! · Catalan(n).
```

Dividing by `n! = (n+1)!/(n+1)` gives the normalized identity used by the second-Ursell
closure.

## Suggested Lean milestones

1. Define or import a Prüfer equivalence between complete-graph spanning trees on
   `Fin (n + 1)` and words of length `n - 1` over `Fin (n + 1)`.
2. Prove the degree/multiplicity relation under that equivalence.
3. Translate degree to `rootedChildCount`, treating root `0` separately.
4. Group words by their occurrence profile and use the existing finite profile
   infrastructure where possible.
5. Prove the multinomial fixed-profile count.
6. Evaluate `Σ (a 0 + 1)` over the relevant `Finset.piAntidiag`.
7. cast the exact natural-number identity to the normalized real statement.

The finite checker in `scripts/check_finite_catalan.py` mirrors these milestones with
exact integer arithmetic. It is regression evidence and a specification aid; it is not a
substitute for any of the Lean steps above.
