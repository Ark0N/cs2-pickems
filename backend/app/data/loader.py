"""Assemble a ready-to-simulate StageState + map-probability matrix from data.

Hybrid strategy: seed roster + seed-prior ratings always work offline; HLTV ranking
(if reachable) refines ratings; betting odds (if a key is set) override the win
probability for concrete matchups. Anything unavailable is silently skipped.
"""

from __future__ import annotations

import numpy as np

from app.config import settings
from app.data.cologne2026 import stage1_teams, stage2_teams, stage3_teams
from app.data.hltv import HLTVClient, rank_order_to_ratings
from app.data.odds import fixtures_to_prob_map, make_odds_client
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
) -> tuple[list[Team], dict]:
    """Fill team ratings. Priority: Valve VRS (no key) > HLTV ranking > seed prior.

    Returns the rated teams plus a provenance dict describing which source was
    actually used (and notes for any requested source that didn't take effect).
    """
    teams = apply_seed_ratings(teams)  # transparent baseline, always present
    prov: dict = {
        "source": "seed",
        "label": "seed prior",
        "detail": "published-seeding prior (offline baseline)",
        "requested": {"valve": use_valve, "hltv": use_hltv},
        "notes": [],
    }
    if use_valve:
        points = ValveStandingsClient().latest_global_points()
        matched = {t.name: points[t.name] for t in teams if t.name in points}
        if len(matched) >= 4:  # enough of the field to rescale meaningfully
            ratings = points_to_ratings(matched)
            teams = [t.model_copy(update={"rating": ratings.get(t.name, t.rating)}) for t in teams]
            prov.update(
                source="valve",
                label="Valve VRS",
                detail=f"{len(matched)}/{len(teams)} teams matched to Global Standings",
            )
            if use_hltv:
                prov["notes"].append(
                    "HLTV not applied — Valve VRS has priority; turn off Valve to use HLTV."
                )
            return teams, prov
        prov["notes"].append(
            f"Valve VRS requested but only {len(matched)} field team(s) matched "
            "(need ≥4); using seed prior."
        )
    if use_hltv:
        order = HLTVClient().world_ranking_order()
        if order:
            ratings = rank_order_to_ratings(order)
            teams = [t.model_copy(update={"rating": ratings.get(t.name, t.rating)}) for t in teams]
            prov.update(source="hltv", label="HLTV ranking", detail=f"{len(order)} ranked teams")
            return teams, prov
        prov["notes"].append(
            "HLTV ranking requested but unavailable (Cloudflare/empty); using seed prior."
        )
    return teams, prov


def build_stage(
    stage: int,
    results: list[MatchResult] | None = None,
    use_hltv: bool = False,
    use_valve: bool = False,
    stage1_advancers: list[str] | None = None,
    stage2_advancers: list[str] | None = None,
) -> StageState:
    teams, ratings_source = apply_ratings(
        base_teams(stage, stage1_advancers, stage2_advancers),
        use_hltv=use_hltv,
        use_valve=use_valve,
    )
    return StageState(
        stage=stage,
        teams=teams,
        results=results or [],
        bo3_all=(stage == 3),
        ratings_source=ratings_source,
    )


def odds_override_probs(
    stage_state: StageState, use_odds: bool = True, tournament: str = "IEM Cologne"
) -> tuple[dict[frozenset[str], dict[str, float]], dict]:
    """Market-implied per-matchup probabilities + provenance describing the source.

    Returns ({} , provenance) whenever odds are off/unavailable/unmatched, so the
    caller can both fall back cleanly and tell the user exactly what happened.
    """
    prov: dict = {
        "provider": settings.odds_provider,
        "keyless": None,
        "requested": use_odds,
        "fixtures": 0,
        "applied_matchups": 0,
        "available": False,
        "note": None,
    }
    if not use_odds:
        prov["note"] = "betting odds not requested"
        return {}, prov
    client = make_odds_client()
    if client is None:
        prov["note"] = "odds provider disabled (odds_provider=none)"
        return {}, prov
    prov["provider"] = client.provider
    prov["keyless"] = client.keyless
    if not client.enabled:
        prov["note"] = f"{client.provider} unavailable (set ODDS_API_KEY)"
        return {}, prov
    prov["available"] = True
    fixtures = client.fetch_fixtures(tournament)
    prov["fixtures"] = len(fixtures)
    probs = fixtures_to_prob_map(fixtures, set(stage_state.team_names))
    prov["applied_matchups"] = len(probs)
    if not probs:
        prov["note"] = (
            "no live odds for the field yet"
            if not fixtures
            else f"{len(fixtures)} fixtures fetched, none between two field teams"
        )
    return probs, prov


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
