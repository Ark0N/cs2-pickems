import numpy as np

from app.data.cologne2026 import stage1_teams
from app.feasibility import analyze_pick, impossible_three_oh_pairs
from app.models import PickEm, StageState
from app.optimizer import evaluate, optimize
from app.ratings import apply_seed_ratings
from app.simulate import StageSimulation, simulate_stage


def _synthetic_sim(n=16, n_sims=1000) -> StageSimulation:
    """Hand-crafted samples where T0 and T1 can NEVER both go 3-0.

    T0 is 3-0 in the first 520 sims, T1 in the rest (disjoint -> P(both)=0). T2
    co-occurs with each, so it is a feasible 3-0 partner. T0/T1 carry the two
    highest 3-0 marginals, so the *unconstrained* optimum picks the impossible
    {T0, T1} pair while the *feasible* optimum must avoid it.
    """
    names = [f"T{i}" for i in range(n)]
    s30 = np.zeros((n_sims, n), dtype=bool)
    s03 = np.zeros((n_sims, n), dtype=bool)
    sadv = np.zeros((n_sims, n), dtype=bool)

    s30[0:520, 0] = True
    s30[520:1000, 1] = True
    s30[0:50, 2] = True  # co-occurs with T0
    s30[520:570, 2] = True  # co-occurs with T1

    sadv[:, 6:14] = True  # eight clear advancers
    sadv[:, [0, 1, 2]] = True  # 3-0 teams also advance
    s03[:, [14, 15]] = True  # two clear wooden-spooners

    return StageSimulation(
        names=names,
        n_sims=n_sims,
        p_advance=sadv.mean(0),
        p_three_oh=s30.mean(0),
        p_zero_three=s03.mean(0),
        s_advance=sadv,
        s_three_oh=s30,
        s_zero_three=s03,
    )


def test_pick_is_structurally_valid_on_real_sim():
    state = StageState(stage=1, teams=apply_seed_ratings(stage1_teams()))
    sim = simulate_stage(state, n_sims=4000, rng_seed=3)
    res = optimize(sim)
    p = res.pick
    assert len(p.three_oh) == 2 and len(p.zero_three) == 2 and len(p.advance) == 6
    picks = p.all_picks()
    assert len(set(picks)) == 10  # all distinct
    assert set(picks).issubset(set(sim.names))
    # constraining feasibility can only cost expected points, never gain
    assert res.unconstrained_expected_points >= res.expected_points - 1e-9


def test_unconstrained_picks_the_impossible_pair_constrained_avoids_it():
    sim = _synthetic_sim()
    free = optimize(sim, enforce_feasible=False)
    safe = optimize(sim, enforce_feasible=True)

    assert set(free.pick.three_oh) == {"T0", "T1"}  # greedy grabs the top two marginals
    assert set(safe.pick.three_oh) != {"T0", "T1"}  # feasibility forbids the pair
    assert "T0" in safe.pick.three_oh and "T2" in safe.pick.three_oh
    assert safe.feasibility_enforced
    assert free.expected_points > safe.expected_points  # the safe pick costs a little


def test_impossible_pair_is_detected_and_warned():
    sim = _synthetic_sim()
    assert ("T0", "T1") in impossible_three_oh_pairs(sim)

    bad = PickEm(
        three_oh=["T0", "T1"],
        zero_three=["T14", "T15"],
        advance=["T6", "T7", "T8", "T9", "T10", "T11"],
    )
    warns = analyze_pick(bad, sim)
    impossible = [w for w in warns if w.level == "impossible"]
    assert any({"T0", "T1"} == set(w.teams) for w in impossible)


def test_evaluate_reports_joint_metrics():
    sim = _synthetic_sim()
    pick = PickEm(
        three_oh=["T0", "T2"],
        zero_three=["T14", "T15"],
        advance=["T6", "T7", "T8", "T9", "T10", "T11"],
    )
    m = evaluate(pick, sim)
    assert m["p_both_0_3"] == 1.0  # T14 & T15 always both 0-3
    assert 0.0 <= m["p_both_3_0"] <= 1.0
    assert m["correct_ge"][0] == 1.0  # always at least 0 correct
    assert m["expected_correct"] > 0
