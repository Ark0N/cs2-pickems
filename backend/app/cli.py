"""CLI: simulate a Cologne Major Swiss stage and print the recommended Pick'Em.

    uv run python -m app.cli --stage 1 --sims 50000

Ratings default to a transparent seed-based prior; live odds/HLTV ratings are
wired through the data layer / API. Use this for a quick terminal report or to
sanity-check the engine without the web UI.
"""

from __future__ import annotations

import argparse

from app.data.cologne2026 import stage1_teams
from app.models import StageState
from app.optimizer import optimize
from app.ratings import apply_seed_ratings
from app.report import format_report
from app.simulate import simulate_stage


def build_stage(stage: int) -> StageState:
    if stage == 1:
        teams = apply_seed_ratings(stage1_teams())
        return StageState(stage=1, teams=teams)
    raise SystemExit(
        f"stage {stage} needs the advancing teams from the previous stage; "
        "use the API/data layer to assemble it once Stage 1 results are in."
    )


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="CS2 Cologne Major Pick'Em optimizer")
    ap.add_argument("--stage", type=int, default=1, choices=[1, 2, 3])
    ap.add_argument("--sims", type=int, default=50_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--allow-impossible",
        action="store_true",
        help="do not enforce joint feasibility on the 3-0 / 0-3 pairs",
    )
    args = ap.parse_args(argv)

    state = build_stage(args.stage)
    sim = simulate_stage(state, n_sims=args.sims, rng_seed=args.seed)
    result = optimize(sim, enforce_feasible=not args.allow_impossible)
    print(format_report(sim, result, state, title=f"IEM Cologne Major 2026 — Stage {args.stage}"))


if __name__ == "__main__":
    main()
