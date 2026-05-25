"""CLI: simulate a Cologne Major Swiss stage and print the recommended Pick'Em.

    uv run python -m app.cli --stage 1 --sims 50000

Ratings default to a transparent seed-based prior; live odds/HLTV ratings are
wired through the data layer / API. Use this for a quick terminal report or to
sanity-check the engine without the web UI.
"""

from __future__ import annotations

import argparse

from app.data.loader import build_map_probs, build_stage, odds_override_probs
from app.optimizer import optimize
from app.report import format_report
from app.simulate import simulate_stage


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
    ap.add_argument(
        "--use-odds", action="store_true", help="pull betting odds (needs ODDS_API_KEY)"
    )
    ap.add_argument(
        "--use-hltv", action="store_true", help="refine ratings from HLTV ranking"
    )
    ap.add_argument("--objective", choices=["category", "ev"], default="category")
    args = ap.parse_args(argv)

    if args.stage != 1:
        raise SystemExit(
            f"stage {args.stage} needs the advancing teams from the previous stage; "
            "use the API once earlier-stage results are in."
        )

    state = build_stage(args.stage, use_hltv=args.use_hltv)
    probs = build_map_probs(state, odds_override_probs(state, use_odds=args.use_odds))
    sim = simulate_stage(state, map_probs=probs, n_sims=args.sims, rng_seed=args.seed)
    result = optimize(sim, objective=args.objective, enforce_feasible=not args.allow_impossible)
    print(format_report(sim, result, state, title=f"IEM Cologne Major 2026 — Stage {args.stage}"))


if __name__ == "__main__":
    main()
