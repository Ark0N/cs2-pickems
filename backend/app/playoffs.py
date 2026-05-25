"""Playoff bracket simulation.

8 teams, single elimination, quarter/semi finals Bo3 and the Grand Final Bo5.
Standard single-elim seeding (1v8, 4v5, 2v7, 3v6) so higher seeds meet later.
Monte Carlo gives each team's probability of reaching the semifinal, the final,
and winning the Major.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

from app.models import SimResult, Team, TeamProb
from app.ratings import map_prob_matrix, series_win_prob

# bracket positions expressed as seed numbers (1 = top seed)
STANDARD_SEED_ORDER = [1, 8, 4, 5, 2, 7, 3, 6]


@dataclass
class PlayoffSimulation:
    names: list[str]
    n_sims: int
    p_semifinal: np.ndarray  # reached the final 4 (won QF)
    p_final: np.ndarray  # reached the Grand Final (won SF)
    p_champion: np.ndarray  # won the Major

    @property
    def index(self) -> dict[str, int]:
        return {n: i for i, n in enumerate(self.names)}

    def champion_pick(self) -> str:
        return self.names[int(np.argmax(self.p_champion))]

    def to_result(self) -> SimResult:
        probs = [
            TeamProb(
                team=self.names[i],
                p_3_0=round(float(self.p_champion[i]), 4),  # reuse field: champion
                p_0_3=round(float(self.p_final[i]), 4),  # reuse field: final
                p_advance=round(float(self.p_semifinal[i]), 4),  # reuse field: semifinal
            )
            for i in range(len(self.names))
        ]
        probs.sort(key=lambda p: -p.p_3_0)
        return SimResult(stage=4, n_sims=self.n_sims, team_probs=probs)


def bracket_order(teams: list[Team]) -> list[int]:
    """Team indices placed into the 8 standard single-elim bracket positions."""
    by_seed = sorted(range(len(teams)), key=lambda i: teams[i].seed)
    return [by_seed[s - 1] for s in STANDARD_SEED_ORDER]


def simulate_playoffs(
    teams: list[Team],
    map_probs: np.ndarray | None = None,
    n_sims: int = 50_000,
    rng_seed: int = 0,
    order: list[int] | None = None,
) -> PlayoffSimulation:
    n = len(teams)
    if n != 8:
        raise ValueError("playoffs need exactly 8 teams")
    if map_probs is None:
        map_probs = map_prob_matrix(teams)
    if order is None:
        order = bracket_order(teams)
    rng = random.Random(rng_seed)

    semi = np.zeros(n)
    final = np.zeros(n)
    champ = np.zeros(n)

    def play(a: int, b: int, bo: int) -> int:
        p = series_win_prob(float(map_probs[a, b]), bo)
        return a if rng.random() < p else b

    for _ in range(n_sims):
        qf = [play(order[k], order[k + 1], 3) for k in range(0, 8, 2)]
        for w in qf:
            semi[w] += 1
        sf = [play(qf[0], qf[1], 3), play(qf[2], qf[3], 3)]
        for w in sf:
            final[w] += 1
        champ[play(sf[0], sf[1], 5)] += 1

    return PlayoffSimulation(
        names=[t.name for t in teams],
        n_sims=n_sims,
        p_semifinal=semi / n_sims,
        p_final=final / n_sims,
        p_champion=champ / n_sims,
    )
