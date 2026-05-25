"""Analysis orchestration, independent of the web framework so it can be tested
directly. The FastAPI layer (app.main) is a thin wrapper over these functions.
"""

from __future__ import annotations

import numpy as np

from app.cosmetics import cosmetic_recommendations
from app.data.cologne2026 import STAGE3_INVITES
from app.data.loader import build_map_probs, build_stage, odds_override_probs
from app.feasibility import analyze_pick, impossible_three_oh_pairs
from app.models import MatchResult, Team
from app.optimizer import evaluate, optimize
from app.playoffs import simulate_playoffs
from app.ratings import apply_seed_ratings
from app.simulate import simulate_stage
from app.swiss import live_bracket


def run_analysis(
    stage: int = 1,
    n_sims: int = 20_000,
    objective: str = "category",
    enforce_feasible: bool = True,
    use_hltv: bool = False,
    use_valve: bool = False,
    use_odds: bool = False,
    results: list[MatchResult] | None = None,
    rating_overrides: dict[str, float] | None = None,
    matchup_overrides: list[dict] | None = None,
    stage1_advancers: list[str] | None = None,
    stage2_advancers: list[str] | None = None,
    rng_seed: int = 0,
) -> dict:
    state = build_stage(
        stage,
        results=results,
        use_hltv=use_hltv,
        use_valve=use_valve,
        stage1_advancers=stage1_advancers,
        stage2_advancers=stage2_advancers,
    )
    if len(state.teams) != 16:
        raise ValueError(
            f"stage {stage} has {len(state.teams)} teams; provide the 8 advancers "
            "from the previous stage to form the 16-team field."
        )

    if rating_overrides:
        state.teams = [
            t.model_copy(update={"rating": rating_overrides.get(t.name, t.rating)})
            for t in state.teams
        ]

    odds_probs, odds_source = odds_override_probs(state, use_odds=use_odds)
    probs = build_map_probs(state, odds_probs)
    if matchup_overrides:
        idx = {n: i for i, n in enumerate(state.team_names)}
        for mo in matchup_overrides:
            a, b, pa = mo["team_a"], mo["team_b"], float(mo["p_a"])
            if a in idx and b in idx:
                probs[idx[a], idx[b]] = pa
                probs[idx[b], idx[a]] = 1.0 - pa

    sim = simulate_stage(state, map_probs=probs, n_sims=n_sims, rng_seed=rng_seed)
    result = optimize(sim, objective=objective, enforce_feasible=enforce_feasible)
    metrics = evaluate(result.pick, sim)
    warnings = analyze_pick(result.pick, sim, state)
    lb = live_bracket(state)

    order = sorted(range(len(sim.names)), key=lambda i: -sim.p_advance[i])
    team_probs = [
        {
            "team": sim.names[i],
            "p_advance": round(float(sim.p_advance[i]), 4),
            "p_three_oh": round(float(sim.p_three_oh[i]), 4),
            "p_zero_three": round(float(sim.p_zero_three[i]), 4),
        }
        for i in order
    ]

    return {
        "stage": stage,
        "n_sims": n_sims,
        "teams": [
            {"name": t.name, "seed": t.seed, "rating": round(t.rating, 1)} for t in state.teams
        ],
        "standings": lb["standings"],
        "current_round": lb["current_round"],
        "complete": lb["complete"],
        "team_probs": team_probs,
        "recommendation": {
            "pick": result.pick.model_dump(),
            "objective": result.objective,
            "expected_points": result.expected_points,
            "expected_correct": result.expected_correct,
            "feasibility_enforced": result.feasibility_enforced,
            "unconstrained_expected_points": result.unconstrained_expected_points,
            "metrics": metrics,
        },
        "warnings": [w.model_dump() for w in warnings],
        "impossible_three_oh_pairs": impossible_three_oh_pairs(sim),
        "data_sources": {"ratings": state.ratings_source, "odds": odds_source},
    }


def run_playoffs(
    team_names: list[str] | None = None,
    rating_overrides: dict[str, float] | None = None,
    n_sims: int = 30_000,
    rng_seed: int = 0,
) -> dict:
    names = team_names or STAGE3_INVITES
    if len(names) != 8:
        raise ValueError("playoffs need exactly 8 teams")
    teams = apply_seed_ratings([Team(name=n, seed=i + 1) for i, n in enumerate(names)])
    if rating_overrides:
        teams = [
            t.model_copy(update={"rating": rating_overrides.get(t.name, t.rating)}) for t in teams
        ]

    psim = simulate_playoffs(teams, n_sims=n_sims, rng_seed=rng_seed)
    ranking = [psim.names[i] for i in np.argsort(-psim.p_champion)]
    probs = [
        {
            "team": psim.names[i],
            "p_semifinal": round(float(psim.p_semifinal[i]), 4),
            "p_final": round(float(psim.p_final[i]), 4),
            "p_champion": round(float(psim.p_champion[i]), 4),
        }
        for i in np.argsort(-psim.p_champion)
    ]
    return {
        "n_sims": n_sims,
        "champion_pick": psim.champion_pick(),
        "team_probs": probs,
        "cosmetics": cosmetic_recommendations(ranking),
    }
