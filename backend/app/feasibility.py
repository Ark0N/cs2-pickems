"""Feasibility & risk analysis for a Pick'Em.

Turns the Monte Carlo joint structure into plain-English warnings. The headline
case is the user's: two teams placed in the 3-0 slot that can never *both* finish
3-0 because their paths must collide (e.g. they meet in the match that decides the
3-0 spot). That shows up as P(both 3-0) == 0 across all simulations.
"""

from __future__ import annotations

from itertools import combinations

from app.models import PickEm, StageState, Warning_
from app.optimizer import _joint_matrix
from app.simulate import StageSimulation
from app.swiss import live_bracket

# thresholds (tunable)
IMPOSSIBLE_EPS = 0.0  # P(both) <= this -> impossible
RISK_PAIR = 0.03  # P(both) below this -> long shot
RISK_ADVANCE = 0.40  # advance pick less likely than this -> risky
RISK_THREE_OH = 0.12  # 3-0 pick less likely than this -> risky
RISK_ZERO_THREE = 0.12  # 0-3 pick less likely than this -> risky


def _meet_note(stage_state: StageState | None, a: str, b: str) -> str:
    """If the two teams are paired in the current live round, say so explicitly."""
    if stage_state is None:
        return ""
    cur = live_bracket(stage_state).get("current_round") or []
    for m in cur:
        if {m["team_a"], m["team_b"]} == {a, b}:
            return f" — they play each other right now in the {m['record']} match"
    return ""


def analyze_pick(
    pick: PickEm,
    sim: StageSimulation,
    stage_state: StageState | None = None,
) -> list[Warning_]:
    idx = sim.index
    j30 = _joint_matrix(sim.s_three_oh)
    j03 = _joint_matrix(sim.s_zero_three)
    warnings: list[Warning_] = []

    # --- 3-0 pair joint feasibility ---
    a, b = pick.three_oh
    pj = float(j30[idx[a], idx[b]])
    if pj <= IMPOSSIBLE_EPS:
        warnings.append(
            Warning_(
                level="impossible",
                message=(
                    f"{a} and {b} can never BOTH finish 3-0"
                    f"{_meet_note(stage_state, a, b)}. At most one of your two 3-0 picks "
                    f"can hit — swap one out."
                ),
                teams=[a, b],
            )
        )
    elif pj < RISK_PAIR:
        warnings.append(
            Warning_(
                level="risk",
                message=f"Both {a} and {b} going 3-0 only happens in {pj:.1%} of simulations.",
                teams=[a, b],
            )
        )

    # --- 0-3 pair joint feasibility ---
    c, d = pick.zero_three
    pj = float(j03[idx[c], idx[d]])
    if pj <= IMPOSSIBLE_EPS:
        warnings.append(
            Warning_(
                level="impossible",
                message=(
                    f"{c} and {d} can never BOTH finish 0-3"
                    f"{_meet_note(stage_state, c, d)}. Swap one out."
                ),
                teams=[c, d],
            )
        )
    elif pj < RISK_PAIR:
        warnings.append(
            Warning_(
                level="risk",
                message=f"Both {c} and {d} going 0-3 only happens in {pj:.1%} of simulations.",
                teams=[c, d],
            )
        )

    # --- per-pick long shots ---
    for t in pick.three_oh:
        p = float(sim.p_three_oh[idx[t]])
        if p < RISK_THREE_OH:
            warnings.append(
                Warning_(
                    level="risk",
                    message=f"{t} reaches 3-0 only {p:.1%} of the time.",
                    teams=[t],
                )
            )
    for t in pick.zero_three:
        p = float(sim.p_zero_three[idx[t]])
        if p < RISK_ZERO_THREE:
            warnings.append(
                Warning_(level="risk", message=f"{t} ends 0-3 only {p:.1%} of the time.", teams=[t])
            )
    for t in pick.advance:
        p = float(sim.p_advance[idx[t]])
        if p < RISK_ADVANCE:
            warnings.append(
                Warning_(
                    level="risk",
                    message=f"{t} advances only {p:.1%} of the time — shaky advance pick.",
                    teams=[t],
                )
            )
    return warnings


def impossible_three_oh_pairs(sim: StageSimulation) -> list[tuple[str, str]]:
    """All team pairs that can never both finish 3-0 (for UI highlighting)."""
    j30 = _joint_matrix(sim.s_three_oh)
    out = []
    for i, j in combinations(range(len(sim.names)), 2):
        # only meaningful when each team can individually 3-0
        if sim.p_three_oh[i] > 0 and sim.p_three_oh[j] > 0 and j30[i, j] <= IMPOSSIBLE_EPS:
            out.append((sim.names[i], sim.names[j]))
    return out
