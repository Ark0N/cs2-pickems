import numpy as np

from app.data.cologne2026 import stage1_teams
from app.models import PickEm, StageState
from app.ratings import apply_seed_ratings
from app.scoring import score_outcome
from app.simulate import simulate_stage


def _sim(n_sims=4000):
    teams = apply_seed_ratings(stage1_teams())
    state = StageState(stage=1, teams=teams)
    return simulate_stage(state, n_sims=n_sims, rng_seed=7)


def test_marginal_totals_match_structure():
    sim = _sim()
    # exactly 8 advance, 2 go 3-0, 2 go 0-3 every sim -> expected sums
    assert abs(sim.p_advance.sum() - 8.0) < 1e-9
    assert abs(sim.p_three_oh.sum() - 2.0) < 1e-9
    assert abs(sim.p_zero_three.sum() - 2.0) < 1e-9


def test_three_oh_implies_advance():
    sim = _sim()
    # P(3-0) <= P(advance) for every team
    assert np.all(sim.p_three_oh <= sim.p_advance + 1e-12)


def test_top_seed_favoured_over_bottom_seed():
    sim = _sim()
    idx = sim.index
    teams = stage1_teams()
    top, bottom = teams[0].name, teams[-1].name
    assert sim.p_advance[idx[top]] > sim.p_advance[idx[bottom]]
    assert sim.p_three_oh[idx[top]] > sim.p_three_oh[idx[bottom]]


def test_score_outcome_counts_correctly():
    pick = PickEm(
        three_oh=["A", "B"],
        zero_three=["C", "D"],
        advance=["E", "F", "G", "H", "I", "J"],
    )
    res = score_outcome(
        pick,
        three_oh={"A", "Z"},  # A correct, B wrong
        zero_three={"C"},  # C correct, D wrong
        advanced={"E", "F", "G"},  # 3 of 6
    )
    assert res["correct_3_0"] == 1
    assert res["correct_0_3"] == 1
    assert res["correct_advance"] == 3
    assert res["correct"] == 5
    assert res["points"] == 5.0
