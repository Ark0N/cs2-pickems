"""Pick'Em optimizer.

Chooses the 10 picks (2x 3-0, 2x 0-3, 6x advance) that maximise expected Pick'Em
points. Expected points is linear, so given a fixed 3-0 pair and 0-3 pair the six
advance picks are simply the highest P(advance) of the remaining teams — which
makes an exact brute force over all (3-0 pair x 0-3 pair) combinations cheap
(~10.9k combos).

Crucially it can also *constrain* the 3-0 and 0-3 pairs to be jointly feasible —
i.e. it refuses to put two teams in the 3-0 slot when they can never both finish
3-0 (the classic "they have to play each other" case). That feasibility comes
straight from the Monte Carlo joint samples, so it works before and during the
event.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np

from app.models import PickEm
from app.scoring import DEFAULT_WEIGHTS, ScoreWeights
from app.simulate import StageSimulation


@dataclass
class OptimizeResult:
    pick: PickEm
    expected_points: float
    expected_correct: float
    feasibility_enforced: bool
    # expected points of the unconstrained optimum, for comparison
    unconstrained_expected_points: float


def _joint_matrix(samples: np.ndarray) -> np.ndarray:
    """P(i and j both true in the same sim) for every pair, as an (n, n) matrix."""
    f = samples.astype(np.float64)
    return (f.T @ f) / samples.shape[0]


def _best_pick_for(
    sim: StageSimulation,
    weights: ScoreWeights,
    feasible_30: np.ndarray,
    feasible_03: np.ndarray,
) -> tuple[PickEm, float]:
    """Exact brute force given which 3-0 / 0-3 pairs are allowed."""
    n = len(sim.names)
    p30 = sim.p_three_oh * weights.three_oh
    p03 = sim.p_zero_three * weights.zero_three
    padv = sim.p_advance * weights.advance

    best_total = -np.inf
    best: tuple[tuple[int, int], tuple[int, int], list[int]] | None = None

    for a, b in combinations(range(n), 2):
        if not feasible_30[a, b]:
            continue
        v30 = p30[a] + p30[b]
        rest = [t for t in range(n) if t != a and t != b]
        for c, d in combinations(rest, 2):
            if not feasible_03[c, d]:
                continue
            v03 = p03[c] + p03[d]
            adv_pool = [t for t in rest if t != c and t != d]
            # top 6 by P(advance)
            adv_pool.sort(key=lambda t: -padv[t])
            adv = adv_pool[:6]
            total = v30 + v03 + padv[adv].sum()
            if total > best_total:
                best_total = total
                best = ((a, b), (c, d), adv)

    assert best is not None, "no feasible pick found"
    (a, b), (c, d), adv = best
    pick = PickEm(
        three_oh=[sim.names[a], sim.names[b]],
        zero_three=[sim.names[c], sim.names[d]],
        advance=[sim.names[t] for t in adv],
    )
    return pick, float(best_total)


def optimize(
    sim: StageSimulation,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
    enforce_feasible: bool = True,
    eps: float = 0.0,
) -> OptimizeResult:
    """Maximise expected Pick'Em points.

    When `enforce_feasible`, the 3-0 pair and 0-3 pair are restricted to pairs that
    co-occur in at least `eps` (fraction) of simulations — so impossible pairs are
    excluded. The unconstrained optimum is also computed for comparison.
    """
    n = len(sim.names)
    j30 = _joint_matrix(sim.s_three_oh)
    j03 = _joint_matrix(sim.s_zero_three)

    all_true = np.ones((n, n), dtype=bool)
    _, unconstrained_pts = _best_pick_for(sim, weights, all_true, all_true)

    if enforce_feasible:
        feas30 = j30 > eps
        feas03 = j03 > eps
        # guard: if the field is so lopsided that fewer than one feasible pair
        # exists, fall back to unconstrained rather than failing.
        if feas30.sum() < 2 or feas03.sum() < 2:
            feas30, feas03 = all_true, all_true
            enforce_feasible = False
    else:
        feas30, feas03 = all_true, all_true

    pick, pts = _best_pick_for(sim, weights, feas30, feas03)
    metrics = evaluate(pick, sim, weights)
    return OptimizeResult(
        pick=pick,
        expected_points=round(pts, 4),
        expected_correct=metrics["expected_correct"],
        feasibility_enforced=enforce_feasible,
        unconstrained_expected_points=round(unconstrained_pts, 4),
    )


def evaluate(pick: PickEm, sim: StageSimulation, weights: ScoreWeights = DEFAULT_WEIGHTS) -> dict:
    """Rich metrics for a concrete Pick'Em, computed over the full joint samples."""
    idx = sim.index
    i30 = [idx[t] for t in pick.three_oh]
    i03 = [idx[t] for t in pick.zero_three]
    iadv = [idx[t] for t in pick.advance]

    c30 = sim.s_three_oh[:, i30].sum(axis=1)
    c03 = sim.s_zero_three[:, i03].sum(axis=1)
    cadv = sim.s_advance[:, iadv].sum(axis=1)
    correct = c30 + c03 + cadv  # 0..10
    points = weights.three_oh * c30 + weights.zero_three * c03 + weights.advance * cadv

    n_sims = sim.n_sims
    correct_ge = {k: float((correct >= k).mean()) for k in range(0, 11)}
    return {
        "expected_points": round(float(points.mean()), 4),
        "expected_correct": round(float(correct.mean()), 4),
        "p_both_3_0": round(float((c30 == 2).mean()), 4),
        "p_both_0_3": round(float((c03 == 2).mean()), 4),
        "p_all_6_advance": round(float((cadv == 6).mean()), 4),
        "p_all_8_advancing": round(float(((c30 + cadv) == 8).mean()), 4),
        "correct_ge": {k: round(v, 4) for k, v in correct_ge.items()},
        "n_sims": n_sims,
    }
