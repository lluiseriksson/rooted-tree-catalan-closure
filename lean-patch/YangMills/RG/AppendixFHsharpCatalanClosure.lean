/- Copyright (c) 2026 Lluis Eriksson. All rights reserved.
Released under the GNU Affero General Public License v3.0
as described in the file LICENSE.
Authors: Lluis Eriksson -/

import Mathlib.Analysis.SpecialFunctions.Pow.Real

/-!
# Square-root Catalan closure

This file contains the real-valued square-root closure used by the Catalan
majorant.  It is independent of the polymer and rooted-tree APIs.

Oracle target: `[propext, Classical.choice, Quot.sound]`.
-/

namespace YangMills.RG

noncomputable def catalanClosure (M ε : ℝ) : ℝ :=
  (1 - Real.sqrt (1 - 4 * M ^ 2 * ε)) / (2 * M)

noncomputable def geometricClosure (M ε : ℝ) : ℝ :=
  M * ε / (1 - 4 * M ^ 2 * ε)

theorem catalanClosure_fixedPoint
    {M ε : ℝ} (hM : 0 < M) (hε : 0 ≤ ε)
    (hsmall : 4 * M ^ 2 * ε ≤ 1) :
    catalanClosure M ε =
      M * ε + M * (catalanClosure M ε) ^ 2 := by
  have hrad : 0 ≤ 1 - 4 * M ^ 2 * ε := by nlinarith
  have _ : 0 ≤ ε := hε
  have hsqrt_sq : Real.sqrt (1 - 4 * M ^ 2 * ε) ^ 2 =
      1 - 4 * M ^ 2 * ε := by
    exact Real.sq_sqrt hrad
  unfold catalanClosure
  field_simp [ne_of_gt hM, (show (2 : ℝ) * M ≠ 0 by positivity)]
  nlinarith

theorem catalanClosure_nonneg
    {M ε : ℝ} (hM : 0 < M) (hε : 0 ≤ ε)
    (hsmall : 4 * M ^ 2 * ε ≤ 1) :
    0 ≤ catalanClosure M ε := by
  have hrad : 0 ≤ 1 - 4 * M ^ 2 * ε := by nlinarith
  have hrad_le_one : 1 - 4 * M ^ 2 * ε ≤ 1 := by
    have hprod : 0 ≤ 4 * M ^ 2 * ε := by positivity
    linarith
  have hsqrt_le_one : Real.sqrt (1 - 4 * M ^ 2 * ε) ≤ 1 := by
    simpa [Real.sqrt_one] using Real.sqrt_le_sqrt hrad_le_one
  unfold catalanClosure
  exact div_nonneg (by nlinarith) (by positivity)

end YangMills.RG
