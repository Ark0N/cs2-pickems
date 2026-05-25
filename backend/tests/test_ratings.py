import numpy as np

from app.data.cologne2026 import stage1_teams
from app.ratings import (
    apply_seed_ratings,
    devig_two_way,
    map_prob_matrix,
    map_win_prob,
    seed_to_rating,
    series_win_prob,
)


def test_map_win_prob_symmetry_and_monotonicity():
    assert map_win_prob(1500, 1500) == 0.5
    # 400-point gap ≈ 10:1 favourite
    assert abs(map_win_prob(1900, 1500) - 10 / 11) < 1e-9
    # P(A beats B) + P(B beats A) == 1
    assert abs(map_win_prob(1700, 1400) + map_win_prob(1400, 1700) - 1.0) < 1e-12
    # stronger rating gap => higher prob
    assert map_win_prob(1600, 1500) < map_win_prob(1700, 1500)


def test_series_inflation_favours_the_better_team():
    p = 0.6
    assert series_win_prob(p, 1) == p
    assert series_win_prob(p, 3) > p  # favourite gains in Bo3
    assert series_win_prob(p, 5) > series_win_prob(p, 3)  # ...and more in Bo5
    # a coin flip stays a coin flip at any length
    for bo in (1, 3, 5):
        assert abs(series_win_prob(0.5, bo) - 0.5) < 1e-12


def test_devig_sums_to_one_and_orders_correctly():
    p_a, p_b = devig_two_way(1.5, 2.5)  # A is the favourite
    assert abs(p_a + p_b - 1.0) < 1e-12
    assert p_a > p_b


def test_seed_prior_orders_top_seed_highest():
    assert seed_to_rating(1, 16) > seed_to_rating(8, 16) > seed_to_rating(16, 16)


def test_prob_matrix_is_complementary():
    teams = apply_seed_ratings(stage1_teams())
    m = map_prob_matrix(teams)
    n = len(teams)
    assert m.shape == (n, n)
    # M[i,j] + M[j,i] == 1 off-diagonal
    assert np.allclose(m + m.T, np.ones((n, n)))
    # top seed beats bottom seed with high probability
    assert m[0, -1] > 0.8
