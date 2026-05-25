"""CLI: simulate Cologne Major Swiss stage(s) and print the recommended Pick'Em.

    uv run python -m app.cli --stage 1 --sims 50000
    uv run python -m app.cli --stage all --sims 50000   # every stage + playoff champ

Stages 2 and 3 have no fixed field — they are built from the previous stage's
advancers. With no results entered the CLI cascades each stage's *expected* top 8
into the next, so `--stage 2`, `--stage 3` and `--stage all` all work pre-event.

Ratings default to a transparent seed-based prior; pass --use-valve / --use-hltv /
--use-odds to refine them via the data layer.
"""

from __future__ import annotations

import argparse

from app.report import format_full_pickem, format_stage
from app.service import run_analysis, run_full_pickem


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="CS2 Cologne Major Pick'Em optimizer")
    ap.add_argument(
        "--stage",
        default="1",
        choices=["1", "2", "3", "all"],
        help="Swiss stage to optimize, or 'all' for every stage + playoff champion",
    )
    ap.add_argument("--sims", type=int, default=50_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--allow-impossible",
        action="store_true",
        help="do not enforce joint feasibility on the 3-0 / 0-3 pairs",
    )
    ap.add_argument(
        "--use-odds", action="store_true", help="pull betting odds (keyless Bovada by default)"
    )
    ap.add_argument(
        "--use-hltv", action="store_true", help="refine ratings from HLTV ranking"
    )
    ap.add_argument(
        "--use-valve", action="store_true", help="ratings from Valve VRS standings (free, no key)"
    )
    ap.add_argument("--objective", choices=["category", "ev"], default="category")
    args = ap.parse_args(argv)

    common = dict(
        n_sims=args.sims,
        objective=args.objective,
        enforce_feasible=not args.allow_impossible,
        use_hltv=args.use_hltv,
        use_valve=args.use_valve,
        use_odds=args.use_odds,
        rng_seed=args.seed,
    )

    if args.stage == "all":
        full = run_full_pickem(**common)
        print(format_full_pickem(full))
    else:
        stage = run_analysis(stage=int(args.stage), **common)
        print(format_stage(stage))


if __name__ == "__main__":
    main()
