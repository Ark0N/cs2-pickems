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
from app.simulate import StageSimulation, simulate_stage
from app.swiss import live_bracket

# Each Swiss stage advances its top 8 into the next stage (Stage 3's top 8 reach
# the playoffs). The CS2 Major Pick'Em offers one entry per Swiss stage.
ADVANCE_SLOTS = 8
STAGE_LABELS = {1: "Challengers", 2: "Legends", 3: "Champions"}


def expected_advancers(sim: StageSimulation, k: int = ADVANCE_SLOTS) -> list[str]:
    """The k most-likely-to-advance teams — the modal field fed into the next stage."""
    order = sorted(range(len(sim.names)), key=lambda i: -sim.p_advance[i])
    return [sim.names[i] for i in order[:k]]


def _simulate_stage_state(
    stage: int,
    *,
    n_sims: int,
    use_hltv: bool,
    use_valve: bool,
    use_odds: bool,
    results: list[MatchResult] | None,
    rating_overrides: dict[str, float] | None,
    matchup_overrides: list[dict] | None,
    stage1_advancers: list[str] | None,
    stage2_advancers: list[str] | None,
    rng_seed: int,
):
    """Build a 16-team stage, apply overrides, and run the Monte Carlo simulation.

    Returns (state, sim, odds_source). Raises ValueError if the field isn't 16 teams
    (i.e. the previous stage's advancers weren't supplied for stage 2/3).
    """
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
    return state, sim, odds_source


def _resolve_cascade(
    stage: int,
    *,
    stage1_advancers: list[str] | None,
    stage2_advancers: list[str] | None,
    auto_cascade: bool,
    n_sims: int,
    use_hltv: bool,
    use_valve: bool,
    use_odds: bool,
    rating_overrides: dict[str, float] | None,
    rng_seed: int,
) -> tuple[list[str] | None, list[str] | None, dict]:
    """Fill in any missing previous-stage advancers by simulating those stages.

    The Pick'Em for stage 2/3 needs a 16-team field, which depends on who advanced
    from earlier stages. When the caller hasn't supplied those advancers (e.g. the
    event hasn't happened yet), we simulate the earlier stages with the same ratings
    and assume each stage's *expected* top 8. Results/matchup overrides are not
    cascaded — they describe the stage being analysed, not the assumed past.

    Returns (stage1_advancers, stage2_advancers, assumed) where `assumed` records
    which advancers were inferred (vs supplied) for transparency.
    """
    assumed: dict = {}
    if stage < 2 or not auto_cascade:
        return stage1_advancers, stage2_advancers, assumed

    common = dict(
        n_sims=n_sims,
        use_hltv=use_hltv,
        use_valve=use_valve,
        use_odds=use_odds,
        results=None,
        rating_overrides=rating_overrides,
        matchup_overrides=None,
        rng_seed=rng_seed,
    )
    if not stage1_advancers:
        _, s1, _ = _simulate_stage_state(
            1, stage1_advancers=None, stage2_advancers=None, **common
        )
        stage1_advancers = expected_advancers(s1)
        assumed["stage1"] = stage1_advancers
    if stage == 3 and not stage2_advancers:
        _, s2, _ = _simulate_stage_state(
            2, stage1_advancers=stage1_advancers, stage2_advancers=None, **common
        )
        stage2_advancers = expected_advancers(s2)
        assumed["stage2"] = stage2_advancers
    return stage1_advancers, stage2_advancers, assumed


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
    auto_cascade: bool = True,
    rng_seed: int = 0,
) -> dict:
    stage1_advancers, stage2_advancers, assumed = _resolve_cascade(
        stage,
        stage1_advancers=stage1_advancers,
        stage2_advancers=stage2_advancers,
        auto_cascade=auto_cascade,
        n_sims=n_sims,
        use_hltv=use_hltv,
        use_valve=use_valve,
        use_odds=use_odds,
        rating_overrides=rating_overrides,
        rng_seed=rng_seed,
    )

    state, sim, odds_source = _simulate_stage_state(
        stage,
        n_sims=n_sims,
        use_hltv=use_hltv,
        use_valve=use_valve,
        use_odds=use_odds,
        results=results,
        rating_overrides=rating_overrides,
        matchup_overrides=matchup_overrides,
        stage1_advancers=stage1_advancers,
        stage2_advancers=stage2_advancers,
        rng_seed=rng_seed,
    )

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
        "stage_label": STAGE_LABELS.get(stage, f"Stage {stage}"),
        "n_sims": n_sims,
        "teams": [
            {"name": t.name, "seed": t.seed, "rating": round(t.rating, 1)} for t in state.teams
        ],
        "standings": lb["standings"],
        "current_round": lb["current_round"],
        "complete": lb["complete"],
        "team_probs": team_probs,
        "expected_advancers": expected_advancers(sim),
        "assumed_advancers": assumed,
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


def run_full_pickem(
    n_sims: int = 20_000,
    objective: str = "category",
    enforce_feasible: bool = True,
    use_hltv: bool = False,
    use_valve: bool = False,
    use_odds: bool = False,
    rating_overrides: dict[str, float] | None = None,
    include_playoffs: bool = True,
    playoff_sims: int = 30_000,
    rng_seed: int = 0,
) -> dict:
    """The complete CS2 Pick'Em: one optimal entry per Swiss stage, cascaded.

    Stage 1 is simulated, its expected top 8 become Stage 2's incoming half, and so
    on; Stage 3's expected top 8 form the playoff field whose champion is picked.
    Each stage's full analysis (probabilities, warnings, impossible pairs) is kept,
    so this is "the whole challenge in one call" rather than three disconnected runs.
    """
    common = dict(
        n_sims=n_sims,
        objective=objective,
        enforce_feasible=enforce_feasible,
        use_hltv=use_hltv,
        use_valve=use_valve,
        use_odds=use_odds,
        rating_overrides=rating_overrides,
        auto_cascade=False,  # we cascade explicitly below so each link is recorded
        rng_seed=rng_seed,
    )

    s1 = run_analysis(stage=1, **common)
    adv1 = s1["expected_advancers"]
    s2 = run_analysis(stage=2, stage1_advancers=adv1, **common)
    adv2 = s2["expected_advancers"]
    s3 = run_analysis(stage=3, stage1_advancers=adv1, stage2_advancers=adv2, **common)
    adv3 = s3["expected_advancers"]

    out: dict = {
        "n_sims": n_sims,
        "objective": objective,
        "stages": [s1, s2, s3],
        "data_sources": s1["data_sources"],
    }
    if include_playoffs:
        out["playoffs"] = run_playoffs(
            team_names=adv3,
            rating_overrides=rating_overrides,
            n_sims=playoff_sims,
            rng_seed=rng_seed,
        )
        out["playoff_field"] = adv3
    return out


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
