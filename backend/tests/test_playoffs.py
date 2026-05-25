import numpy as np

from app.cosmetics import cosmetic_recommendations, recommend_mvp
from app.data.cologne2026 import STAGE3_INVITES
from app.models import Team
from app.playoffs import bracket_order, simulate_playoffs
from app.ratings import apply_seed_ratings


def _eight_teams():
    teams = [Team(name=n, seed=i + 1) for i, n in enumerate(STAGE3_INVITES)]
    return apply_seed_ratings(teams)


def test_bracket_order_is_standard_single_elim():
    teams = _eight_teams()
    order = bracket_order(teams)
    seeds = [teams[i].seed for i in order]
    assert seeds == [1, 8, 4, 5, 2, 7, 3, 6]


def test_playoff_round_probabilities_are_consistent():
    sim = simulate_playoffs(_eight_teams(), n_sims=8000, rng_seed=0)
    assert abs(sim.p_champion.sum() - 1.0) < 1e-9
    assert abs(sim.p_final.sum() - 2.0) < 1e-9
    assert abs(sim.p_semifinal.sum() - 4.0) < 1e-9
    # deeper rounds are never more likely than earlier ones
    assert np.all(sim.p_semifinal + 1e-12 >= sim.p_final)
    assert np.all(sim.p_final + 1e-12 >= sim.p_champion)
    # top seed is the title favourite
    assert int(np.argmax(sim.p_champion)) == 0
    assert sim.champion_pick() == STAGE3_INVITES[0]


def test_cosmetics_pick_known_star_for_top_team():
    mvp = recommend_mvp(["Team Vitality", "Natus Vincere"])
    assert mvp["player"] == "ZywOo" and mvp["team"] == "Team Vitality"
    rec = cosmetic_recommendations(["Team Spirit"])
    assert rec["mvp"]["player"] == "donk"
    assert "map" in rec and "skins" in rec
