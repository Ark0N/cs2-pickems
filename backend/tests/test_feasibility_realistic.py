"""End-to-end check of the headline feature on a realistic Cologne Stage 1 state.

We feed real round 1 + round 2 results so the 2-0 group is exactly
{GamerLegion(1), B8(2), HEROIC(3), BetBoom(4)}. Valve's Buchholz pairing then puts
the round-3 (2-0) matches as 1v4 and 2v3, so GamerLegion & BetBoom can never both
finish 3-0, and neither can B8 & HEROIC. The engine must detect and avoid that.
"""

from app.data.cologne2026 import STAGE1_INVITES as S
from app.feasibility import analyze_pick, impossible_three_oh_pairs
from app.models import MatchResult, PickEm
from app.optimizer import optimize
from app.simulate import simulate_stage
from app.swiss import live_bracket

# round 1: every top seed (1..8) beats its bottom-half opponent (seed+8)
R1 = [(S[i], S[i + 8], S[i]) for i in range(8)]
# round 2, 1-0 group pairs 1v8,2v7,3v6,4v5 -> seeds 1..4 win to 2-0
R2_TOP = [(S[0], S[7], S[0]), (S[1], S[6], S[1]), (S[2], S[5], S[2]), (S[3], S[4], S[3])]
# round 2, 0-1 group pairs 9v16,10v15,11v14,12v13 -> seeds 9..12 win
R2_BOT = [(S[8], S[15], S[8]), (S[9], S[14], S[9]), (S[10], S[13], S[10]), (S[11], S[12], S[11])]

RESULTS = [MatchResult(team_a=a, team_b=b, winner=w) for a, b, w in (*R1, *R2_TOP, *R2_BOT)]


def _build():
    from app.data.loader import build_stage

    state = build_stage(1, results=RESULTS)
    sim = simulate_stage(state, n_sims=8000, rng_seed=1)
    return state, sim


def test_two_zero_group_is_as_expected():
    from app.data.loader import build_stage

    lb = live_bracket(build_stage(1, results=RESULTS))
    two_oh = {m["team_a"] for m in lb["current_round"] if m["record"] == "2-0"} | {
        m["team_b"] for m in lb["current_round"] if m["record"] == "2-0"
    }
    assert two_oh == {S[0], S[1], S[2], S[3]}
    # the 2-0 matches should be Bo3 (advancement matches)
    assert all(m["bo"] == 3 for m in lb["current_round"] if m["record"] == "2-0")


def test_forced_collisions_are_flagged_impossible():
    _, sim = _build()
    pairs = {frozenset(p) for p in impossible_three_oh_pairs(sim)}
    assert frozenset((S[0], S[3])) in pairs  # GamerLegion & BetBoom meet in the 2-0 match
    assert frozenset((S[1], S[2])) in pairs  # B8 & HEROIC meet in the 2-0 match
    # teams in DIFFERENT 2-0 matches can still both 3-0
    assert frozenset((S[0], S[1])) not in pairs


def test_warning_explains_the_clash():
    state, sim = _build()
    bad = PickEm(
        three_oh=[S[0], S[3]],
        zero_three=[S[14], S[15]],
        advance=[S[1], S[2], S[4], S[5], S[6], S[7]],
    )
    warns = analyze_pick(bad, sim, state)
    impossible = [w for w in warns if w.level == "impossible"]
    assert any({S[0], S[3]} == set(w.teams) for w in impossible)
    assert any("play each other" in w.message for w in impossible)


def test_optimizer_avoids_the_impossible_pairs():
    _, sim = _build()
    chosen = set(optimize(sim, enforce_feasible=True).pick.three_oh)
    assert chosen != {S[0], S[3]}
    assert chosen != {S[1], S[2]}
