"""Assemble a ready-to-simulate StageState + map-probability matrix from data.

Hybrid strategy: seed roster + seed-prior ratings always work offline; HLTV ranking
(if reachable) refines ratings; betting odds (if a key is set) override the win
probability for concrete matchups. Anything unavailable is silently skipped.
"""

from __future__ import annotations

import numpy as np

from app.data.cologne2026 import stage1_teams, stage2_teams, stage3_teams
from app.data.hltv import HLTVClient, rank_order_to_ratings
from app.data.odds import OddsClient, fixtures_to_prob_map
from app.data.valve_standings import ValveStandingsClient, points_to_ratings
from app.models import MatchResult, StageState, Team
from app.ratings import apply_seed_ratings, map_prob_matrix


def base_teams(
    stage: int,
    stage1_advancers: list[str] | None = None,
    stage2_advancers: list[str] | None = None,
) -> list[Team]:
    if stage == 1:
        return stage1_teams()
    if stage == 2:
        return stage2_teams(stage1_advancers or [])
    if stage == 3:
        return stage3_teams(stage2_advancers or [])
    raise ValueError("stage must be 1, 2 or 3")


def apply_ratings(
    teams: list[Team], use_hltv: bool = False, use_valve: bool = False
) -> list[Team]:
    """Fill team ratings. Priority: Valve VRS (no key) > HLTV ranking > seed prior."""
    teams = apply_seed_ratings(teams)  # transparent baseline, always present
    if use_valve:
        points = ValveStandingsClient().latest_global_points()
        matched = {t.name: points[t.name] for t in teams if t.name in points}
        if len(matched) >= 4:  # enough of the field to rescale meaningfully
            ratings = points_to_ratings(matched)
            return [t.model_copy(update={"rating": ratings.get(t.name, t.rating)}) for t in teams]
    if use_hltv:
        order = HLTVClient().world_ranking_order()
        if order:
            ratings = rank_order_to_ratings(order)
            return [t.model_copy(update={"rating": ratings.get(t.name, t.rating)}) for t in teams]
    return teams


def build_stage(
    stage: int,
    results: list[MatchResult] | None = None,
    use_hltv: bool = False,
    use_valve: bool = False,
    stage1_advancers: list[str] | None = None,
    stage2_advancers: list[str] | None = None,
) -> StageState:
    teams = apply_ratings(
        base_teams(stage, stage1_advancers, stage2_advancers),
        use_hltv=use_hltv,
        use_valve=use_valve,
    )
    return StageState(stage=stage, teams=teams, results=results or [], bo3_all=(stage == 3))


def odds_override_probs(
    stage_state: StageState, use_odds: bool = True, tournament: str = "IEM Cologne"
) -> dict[frozenset[str], dict[str, float]]:
    if not use_odds:
        return {}
    fixtures = OddsClient().fetch_fixtures(tournament)
    return fixtures_to_prob_map(fixtures, set(stage_state.team_names))


def build_map_probs(
    stage_state: StageState,
    odds_probs: dict[frozenset[str], dict[str, float]] | None = None,
) -> np.ndarray:
    """Ratings-based map-win matrix, with concrete matchups overridden by odds.

    Note: odds give a *match* win prob. For Bo1 matches (most Swiss matches) that
    equals the map prob; for Bo3/Bo5 it slightly overstates the favourite once the
    sim re-inflates for the series. Acceptable approximation — documented.
    """
    m = map_prob_matrix(stage_state.teams)
    if odds_probs:
        idx = {n: i for i, n in enumerate(stage_state.team_names)}
        for pair, probs in odds_probs.items():
            a, b = tuple(pair)
            if a in idx and b in idx:
                m[idx[a], idx[b]] = probs[a]
                m[idx[b], idx[a]] = probs[b]
    return m
