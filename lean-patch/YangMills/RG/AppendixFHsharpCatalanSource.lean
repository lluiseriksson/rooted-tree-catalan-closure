/- Copyright (c) 2026 Lluis Eriksson. All rights reserved.
Released under the GNU Affero General Public License v3.0
as described in the file LICENSE.
Authors: Lluis Eriksson -/

import YangMills.KP.RootedCatalan
import YangMills.RG.AppendixFSecondUrsellLeafSummation
import YangMills.RG.AppendixFHsharpCatalanClosure

/-!
# Conditional Catalan source adapter for Appendix-F second Ursell bounds

This module proves the downstream Appendix-F marked-root leaf bound assuming
the exact rooted child-factorial Catalan identity from
`YangMills.KP.RootedCatalan`.

The identity is an explicit hypothesis, not an axiom.  Consequently theorems
in this file have clean oracle reports, but they do not by themselves close
the missing combinatorial bijection.

Oracle target: `[propext, Classical.choice, Quot.sound]`.
-/

namespace YangMills.RG

open scoped BigOperators

/-- Marked-root second-Ursell leaf summation with the exact Catalan tree-shape
factor, conditional on the exact rooted child-factorial Catalan identity for
this order `n`. -/
theorem appendixFHoleHsharpWeightedTreeMarkedRootSum_le_catalan_of_expWeight
    {d L : ℕ} [NeZero L]
    (HF : HoleFamily d L)
    (zK : Finset (Cube d L) → ℂ)
    (w : OmegaPolymerType HF zK → ℝ)
    (r : Cube d L)
    (n : ℕ)
    (κ₀ : ℝ)
    (hκ₀ : 0 < κ₀)
    (hw : ∀ Q : OmegaPolymerType HF zK, 0 ≤ w Q)
    (hw_exp :
      ∀ Q : OmegaPolymerType HF zK,
        w Q ≤ appendixFHoleExpWeight HF (2 * κ₀) Q.val)
    (hdisj :
      ∀ H₁ ∈ HF.holes, ∀ H₂ ∈ HF.holes,
        H₁ ≠ H₂ → Disjoint H₁ H₂)
    (hnoedges :
      noEdgesBetweenHoles (cubeAdj d L) HF.holes)
    (hholes_ne : ∀ H₀ ∈ HF.holes, H₀.Nonempty)
    (hCq :
      ((3 ^ d : ℕ) : ℝ) ^ 2 *
          (Real.exp (-κ₀) * 2 ^ (3 ^ d + 1)) < 1)
    (hcat : YangMills.KP.RootedChildFactorialCatalanIdentity n) :
    ((n : ℝ) + 1) *
        appendixFHoleHsharpWeightedTreeMarkedRootSum
          HF zK w r n
      ≤
    (catalan n : ℝ) *
      appendixFSecondUrsellMomentConstant d κ₀ ^ (2 * n + 1) := by
  classical
  let topTrees : Finset (Finset (Sym2 (Fin (n + 1)))) :=
    YangMills.KP.spanningTrees (⊤ : SimpleGraph (Fin (n + 1)))
  let M : ℝ := appendixFSecondUrsellMomentConstant d κ₀
  let norm : ℝ := ((n : ℝ) + 1) * (((n + 1).factorial : ℝ))⁻¹
  let S : ℝ :=
    ∑ T ∈ topTrees,
      ∏ v : Fin (n + 1), ((YangMills.KP.rootedChildCount T v).factorial : ℝ)
  have hM_nonneg : 0 ≤ M := by
    simpa [M] using appendixFSecondUrsellMomentConstant_nonneg d κ₀
  have hnorm_nonneg : 0 ≤ norm := by
    dsimp [norm]
    positivity
  have hraw_kernel :
      appendixFHoleHsharpWeightedTreeMarkedRootRawSum HF zK w r n
        ≤
      appendixFHoleHsharpWeightedTreeMarkedRootCompleteParentKernelSum
        HF zK w κ₀ r n := by
    exact
      (appendixFHoleHsharpWeightedTreeMarkedRootRawSum_le_completeTreeParentSum
        HF zK w r n hw).trans
        (appendixFHoleHsharpWeightedTreeMarkedRootCompleteParentSum_le_kernelSum
          HF zK w κ₀ r n hw hw_exp)
  have hkernel :
      appendixFHoleHsharpWeightedTreeMarkedRootCompleteParentKernelSum
          HF zK w κ₀ r n
        ≤
      ∑ T ∈ topTrees,
        (∏ v : Fin (n + 1),
          ((YangMills.KP.rootedChildCount T v).factorial : ℝ)) *
          M ^ (2 * n + 1) := by
    calc
      appendixFHoleHsharpWeightedTreeMarkedRootCompleteParentKernelSum
          HF zK w κ₀ r n
          =
        ∑ T ∈ topTrees,
          appendixFHoleHsharpWeightedTreeMarkedRootFixedParentKernelSum
            HF zK w κ₀ r n T := by
            simpa [topTrees] using
              appendixFHoleHsharpWeightedTreeMarkedRootCompleteParentKernelSum_eq_sum_fixed
                HF zK w κ₀ r n
      _ ≤
        ∑ T ∈ topTrees,
          (∏ v : Fin (n + 1),
            ((YangMills.KP.rootedChildCount T v).factorial : ℝ)) *
            M ^ (2 * n + 1) := by
            refine Finset.sum_le_sum ?_
            intro T hT
            simpa [M] using
              appendixFHoleHsharpWeightedTreeMarkedRootFixedParentKernelSum_le_childFactor_mul_momentPow
                HF zK w κ₀ r n T hT hw hw_exp hκ₀ hdisj hnoedges
                hholes_ne hCq
  have htree_sum : norm * S ≤ (catalan n : ℝ) := by
    simpa [norm, S, topTrees,
      YangMills.KP.rootedChildFactorialTreeSum,
      YangMills.KP.rootedChildFactorialTreeSumNormalized] using
      YangMills.KP.rootedChildCount_factorialTreeSum_normalized_le_catalan_of_identity_raw
        n hcat
  have hsum_const :
      (∑ T ∈ topTrees,
        (∏ v : Fin (n + 1),
          ((YangMills.KP.rootedChildCount T v).factorial : ℝ)) *
          M ^ (2 * n + 1))
        = S * M ^ (2 * n + 1) := by
    dsimp [S]
    rw [Finset.sum_mul]
  calc
    ((n : ℝ) + 1) *
        appendixFHoleHsharpWeightedTreeMarkedRootSum
          HF zK w r n
        =
      norm * appendixFHoleHsharpWeightedTreeMarkedRootRawSum HF zK w r n := by
        rw [appendixFHoleHsharpWeightedTreeMarkedRootSum_eq_inv_factorial_mul_rawSum]
        simp [norm]
        ring
    _ ≤
      norm *
        appendixFHoleHsharpWeightedTreeMarkedRootCompleteParentKernelSum
          HF zK w κ₀ r n := by
        exact mul_le_mul_of_nonneg_left hraw_kernel hnorm_nonneg
    _ ≤
      norm *
        (∑ T ∈ topTrees,
          (∏ v : Fin (n + 1),
            ((YangMills.KP.rootedChildCount T v).factorial : ℝ)) *
            M ^ (2 * n + 1)) := by
        exact mul_le_mul_of_nonneg_left hkernel hnorm_nonneg
    _ =
      M ^ (2 * n + 1) * (norm * S) := by
        rw [hsum_const]
        ring
    _ ≤ M ^ (2 * n + 1) * (catalan n : ℝ) := by
        exact mul_le_mul_of_nonneg_left htree_sum (pow_nonneg hM_nonneg _)
    _ =
      (catalan n : ℝ) *
        appendixFSecondUrsellMomentConstant d κ₀ ^ (2 * n + 1) := by
        simp [M]
        ring

end YangMills.RG
