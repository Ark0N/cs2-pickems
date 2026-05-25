"""Win-probability model.

Produces, for any pair of teams, the probability that one beats the other in a
single map. That single-map probability is then inflated to Bo3 / Bo5 series
probabilities. Inputs, in order of preference:

  1. De-vigged betting odds for a concrete matchup (most accurate, market-calibrated).
  2. An Elo-style rating per team (from HLTV / Valve rankings, or a seed prior).

Ratings use the standard Elo scale: a 400-point gap ≈ a 10:1 favourite per map.
"""

from __future__ import annotations

import numpy as np

from app.models import Team

# --- Elo / map-level probability ------------------------------------------------


def map_win_prob(rating_a: float, rating_b: float) -> float:
    """P(A beats B on a single map) from Elo ratings."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def series_win_prob(p_map: float, bo: int) -> float:
    """Inflate a per-map win prob to a best-of-`bo` series.

    A stronger team is *more* likely to win a longer series, so favourites gain.
    Closed forms: Bo3 = p²(3-2p); Bo5 = p³(6p²-15p+10).
    """
    p = p_map
    if bo == 1:
        return p
    if bo == 3:
        return p * p * (3 - 2 * p)
    if bo == 5:
        return p**3 * (6 * p * p - 15 * p + 10)
    raise ValueError(f"unsupported best-of: {bo}")


# --- Betting odds ---------------------------------------------------------------


def devig_two_way(odd_a: float, odd_b: float) -> tuple[float, float]:
    """Convert two decimal odds into fair probabilities, removing the bookmaker margin.

    Proportional (multiplicative) de-vig: implied probs 1/odd, renormalised to sum 1.
    """
    if odd_a <= 1.0 or odd_b <= 1.0:
        raise ValueError("decimal odds must be > 1.0")
    imp_a, imp_b = 1.0 / odd_a, 1.0 / odd_b
    total = imp_a + imp_b
    return imp_a / total, imp_b / total


def blend(market_p: float | None, model_p: float, market_weight: float = 0.7) -> float:
    """Blend a market probability (if available) with the rating-model probability."""
    if market_p is None:
        return model_p
    w = min(max(market_weight, 0.0), 1.0)
    return w * market_p + (1.0 - w) * model_p


# --- Seed prior + rating assignment ---------------------------------------------


def seed_to_rating(seed: int, n_teams: int, spread: float = 400.0, base: float = 1500.0) -> float:
    """Provisional rating from seed: seed 1 = base + spread/2, last seed = base - spread/2."""
    if n_teams <= 1:
        return base
    mid = (n_teams - 1) / 2.0
    return base + spread * (mid - (seed - 1)) / (n_teams - 1)


def apply_seed_ratings(teams: list[Team], spread: float = 400.0) -> list[Team]:
    """Return copies of `teams` with ratings derived from seed (a transparent prior)."""
    n = len(teams)
    out = []
    for t in teams:
        out.append(t.model_copy(update={"rating": seed_to_rating(t.seed, n, spread)}))
    return out


def map_prob_matrix(teams: list[Team]) -> np.ndarray:
    """NxN matrix M where M[i, j] = P(team i beats team j on one map)."""
    ratings = np.array([t.rating for t in teams], dtype=float)
    diff = ratings[:, None] - ratings[None, :]
    m = 1.0 / (1.0 + 10.0 ** (-diff / 400.0))
    np.fill_diagonal(m, 0.5)
    return m
