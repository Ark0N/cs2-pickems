"""Monte Carlo driver: run many Swiss simulations and tally outcomes.

Produces both per-team marginals (P(3-0), P(0-3), P(advance)) and the full joint
outcome samples. The optimizer needs the joint samples so that mutually exclusive
picks (e.g. two teams that must meet to decide a 3-0 slot) are scored correctly and
impossible combinations fall out automatically.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

from app.models import SimResult, StageState, TeamProb
from app.ratings import map_prob_matrix
from app.swiss import StagePrep, simulate_stage_once


@dataclass
class StageSimulation:
    names: list[str]
    n_sims: int
    p_advance: np.ndarray  # (n,)
    p_three_oh: np.ndarray  # (n,)
    p_zero_three: np.ndarray  # (n,)
    # joint samples, shape (n_sims, n), dtype bool
    s_advance: np.ndarray
    s_three_oh: np.ndarray
    s_zero_three: np.ndarray

    @property
    def index(self) -> dict[str, int]:
        return {name: i for i, name in enumerate(self.names)}

    def to_result(self) -> SimResult:
        probs = [
            TeamProb(
                team=self.names[i],
                p_3_0=round(float(self.p_three_oh[i]), 4),
                p_0_3=round(float(self.p_zero_three[i]), 4),
                p_advance=round(float(self.p_advance[i]), 4),
            )
            for i in range(len(self.names))
        ]
        probs.sort(key=lambda p: -p.p_advance)
        return SimResult(stage=0, n_sims=self.n_sims, team_probs=probs)


def simulate_stage(
    stage_state: StageState,
    map_probs: np.ndarray | None = None,
    n_sims: int = 50_000,
    rng_seed: int = 0,
) -> StageSimulation:
    """Run `n_sims` Swiss simulations of the stage.

    `map_probs` is an NxN single-map win-probability matrix; if omitted it is built
    from the teams' ratings (so apply ratings before calling, or rely on the prior).
    """
    prep = StagePrep(stage_state)
    n = prep.n
    if map_probs is None:
        map_probs = map_prob_matrix(stage_state.teams)
    rng = random.Random(rng_seed)

    s_adv = np.zeros((n_sims, n), dtype=bool)
    s_30 = np.zeros((n_sims, n), dtype=bool)
    s_03 = np.zeros((n_sims, n), dtype=bool)

    for k in range(n_sims):
        wins, losses = simulate_stage_once(prep, map_probs, rng)
        adv = wins == prep.advance_at
        s_adv[k] = adv
        s_30[k] = adv & (losses == 0)
        s_03[k] = (losses == prep.eliminate_at) & (wins == 0)

    return StageSimulation(
        names=prep.names,
        n_sims=n_sims,
        p_advance=s_adv.mean(axis=0),
        p_three_oh=s_30.mean(axis=0),
        p_zero_three=s_03.mean(axis=0),
        s_advance=s_adv,
        s_three_oh=s_30,
        s_zero_three=s_03,
    )
