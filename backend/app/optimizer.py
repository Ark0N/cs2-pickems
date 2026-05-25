"""Pick'Em optimizer.

Chooses the 10 picks (2x 3-0, 2x 0-3, 6x advance). Two objectives are offered,
both of which can constrain the 3-0 / 0-3 pairs to be *jointly feasible* (so the
optimizer refuses to put two teams in the 3-0 slot when they can never both finish
3-0 — the classic "they have to play each other" case). Feasibility comes straight
from the Monte Carlo joint samples, so it works before and during the event.

- "category" (default): fill each slot with its genuinely best candidates — the two
  most-likely-to-3-0 teams, the two most-likely-to-0-3, and the six most-likely-to-
  advance. This matches how people actually want their marquee 3-0 picks chosen and
  maximises expected correct picks *per category*.

- "ev": globally maximise expected total points. This is subtly different: a 3-0
  pick only scores on an exact 3-0, so a strong team is often "worth more" in the
  advance slot. Pure EV therefore tends to sacrifice a borderline team into the 3-0
  slot. Defensible, but unintuitive — offered as an alternative.
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
    objective: str
    expected_points: float
    expected_correct: float
    feasibility_enforced: bool
    # expected points of the same objective WITHOUT the feasibility constraint,
    # so the gap is purely the cost of avoiding impossible pairs.
    unconstrained_expected_points: float


def _joint_matrix(samples: np.ndarray) -> np.ndarray:
    """P(i and j both true in the same sim) for every pair, as an (n, n) matrix."""
    f = samples.astype(np.float64)
    return (f.T @ f) / samples.shape[0]


def _best_feasible_pair(
    values: np.ndarray, feasible: np.ndarray, exclude: set[int]
) -> tuple[int, int]:
    """Pair (i, j) maximising values[i] + values[j] with feasible[i, j], i/j not excluded."""
    n = len(values)
    best: tuple[int, int] | None = None
    best_v = -np.inf
    for i, j in combinations(range(n), 2):
        if i in exclude or j in exclude or not feasible[i, j]:
            continue
        v = values[i] + values[j]
        if v > best_v:
            best_v = v
            best = (i, j)
    if best is None:  # no feasible pair (degenerate) — take the top two by value
        order = sorted((t for t in range(n) if t not in exclude), key=lambda t: -values[t])
        best = (order[0], order[1])
    return best


def _top_advance(padv: np.ndarray, exclude: set[int], k: int = 6) -> list[int]:
    pool = sorted((t for t in range(len(padv)) if t not in exclude), key=lambda t: -padv[t])
    return pool[:k]


def _category_pick(
    sim: StageSimulation, w: ScoreWeights, feas30: np.ndarray, feas03: np.ndarray
) -> PickEm:
    p30 = sim.p_three_oh * w.three_oh
    p03 = sim.p_zero_three * w.zero_three
    padv = sim.p_advance * w.advance
    a, b = _best_feasible_pair(p30, feas30, set())
    c, d = _best_feasible_pair(p03, feas03, {a, b})
    adv = _top_advance(padv, {a, b, c, d})
    return PickEm(
        three_oh=[sim.names[a], sim.names[b]],
        zero_three=[sim.names[c], sim.names[d]],
        advance=[sim.names[t] for t in adv],
    )


def _ev_pick(
    sim: StageSimulation, w: ScoreWeights, feas30: np.ndarray, feas03: np.ndarray
) -> PickEm:
    """Exact global EV optimum: brute force over feasible (3-0 pair x 0-3 pair)."""
    n = len(sim.names)
    p30 = sim.p_three_oh * w.three_oh
    p03 = sim.p_zero_three * w.zero_three
    padv = sim.p_advance * w.advance

    best_total = -np.inf
    best: tuple[tuple[int, int], tuple[int, int], list[int]] | None = None
    for a, b in combinations(range(n), 2):
        if not feas30[a, b]:
            continue
        v30 = p30[a] + p30[b]
        rest = [t for t in range(n) if t != a and t != b]
        for c, d in combinations(rest, 2):
            if not feas03[c, d]:
                continue
            adv = _top_advance(padv, {a, b, c, d})
            total = v30 + p03[c] + p03[d] + padv[adv].sum()
            if total > best_total:
                best_total = total
                best = ((a, b), (c, d), adv)
    assert best is not None, "no feasible pick found"
    (a, b), (c, d), adv = best
    return PickEm(
        three_oh=[sim.names[a], sim.names[b]],
        zero_three=[sim.names[c], sim.names[d]],
        advance=[sim.names[t] for t in adv],
    )


_SELECTORS = {"category": _category_pick, "ev": _ev_pick}


def optimize(
    sim: StageSimulation,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
    objective: str = "category",
    enforce_feasible: bool = True,
    eps: float = 0.0,
) -> OptimizeResult:
    if objective not in _SELECTORS:
        raise ValueError(f"objective must be one of {list(_SELECTORS)}")
    select = _SELECTORS[objective]
    n = len(sim.names)
    all_true = np.ones((n, n), dtype=bool)

    # same objective, no feasibility constraint — the EV ceiling for comparison
    unconstrained = select(sim, weights, all_true, all_true)
    unconstrained_pts = evaluate(unconstrained, sim, weights)["expected_points"]

    feas30 = feas03 = all_true
    if enforce_feasible:
        f30 = _joint_matrix(sim.s_three_oh) > eps
        f03 = _joint_matrix(sim.s_zero_three) > eps
        if f30.sum() >= 2 and f03.sum() >= 2:  # guard against over-constraining
            feas30, feas03 = f30, f03
        else:
            enforce_feasible = False

    pick = select(sim, weights, feas30, feas03)
    metrics = evaluate(pick, sim, weights)
    return OptimizeResult(
        pick=pick,
        objective=objective,
        expected_points=metrics["expected_points"],
        expected_correct=metrics["expected_correct"],
        feasibility_enforced=enforce_feasible,
        unconstrained_expected_points=unconstrained_pts,
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

    correct_ge = {k: float((correct >= k).mean()) for k in range(0, 11)}
    return {
        "expected_points": round(float(points.mean()), 4),
        "expected_correct": round(float(correct.mean()), 4),
        "p_both_3_0": round(float((c30 == 2).mean()), 4),
        "p_both_0_3": round(float((c03 == 2).mean()), 4),
        "p_all_6_advance": round(float((cadv == 6).mean()), 4),
        "p_all_8_advancing": round(float(((c30 + cadv) == 8).mean()), 4),
        "correct_ge": {k: round(v, 4) for k, v in correct_ge.items()},
        "n_sims": sim.n_sims,
    }
