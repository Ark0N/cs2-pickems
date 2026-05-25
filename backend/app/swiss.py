"""Valve-style Swiss stage with Buchholz pairing.

Implements the 16-team Major Swiss used since 2023:
  - Round 1: seeded pairing, top half vs bottom half (1v9, 2v10, ... 8v16).
  - Rounds 2+: teams grouped by W-L record; within a group they are ordered by
    Buchholz (sum of faced opponents' [wins - losses]), then initial seed; the
    best-ranked team is paired against the lowest-ranked team it has NOT already
    played (rematch avoidance).
  - A team stops once it reaches `advance_at` wins (advances) or `eliminate_at`
    losses (eliminated). Max rounds = advance_at + eliminate_at - 1 (= 5).
  - The match that would give a team its final win (advancement) or final loss
    (elimination) is Bo3; all other matches are Bo1 — unless `bo3_all` (Stage 3).

The hot path (`simulate_stage_once`) avoids object overhead: it works on int
arrays plus a stdlib RNG, so the Monte Carlo driver can call it many times.
"""

from __future__ import annotations

import random

import numpy as np

from app.models import StageState
from app.ratings import series_win_prob

Pair = tuple[int, int]


# --- pairing primitives ---------------------------------------------------------


def _initial_pairs(order_by_seed: list[int]) -> list[Pair]:
    """Round 1: index i (seed-sorted) plays index i + half."""
    half = len(order_by_seed) // 2
    return [(order_by_seed[i], order_by_seed[i + half]) for i in range(half)]


def _group_order(
    group: list[int],
    wins: np.ndarray,
    losses: np.ndarray,
    faced: list[list[int]],
    seed: np.ndarray,
) -> list[int]:
    """Order a same-record group best -> worst by (Buchholz desc, seed asc)."""

    def buchholz(i: int) -> int:
        return sum(int(wins[o]) - int(losses[o]) for o in faced[i])

    return sorted(group, key=lambda i: (-buchholz(i), int(seed[i])))


def _pair_group(order: list[int], played: np.ndarray) -> list[Pair]:
    """Pair best vs lowest-unplayed: the Valve 'high seed faces low seed, avoid rematch'."""
    remaining = list(order)
    pairs: list[Pair] = []
    while remaining:
        high = remaining.pop(0)
        if not remaining:  # odd group (shouldn't happen in 16-team Swiss) — give a bye
            break
        opp_pos: int | None = None
        for k in range(len(remaining) - 1, -1, -1):  # scan from the bottom up
            if not played[high, remaining[k]]:
                opp_pos = k
                break
        if opp_pos is None:  # only rematches left (rare) — take the lowest
            opp_pos = len(remaining) - 1
        low = remaining.pop(opp_pos)
        pairs.append((high, low))
    return pairs


def _round_pairings(
    round_idx: int,
    active: list[int],
    wins: np.ndarray,
    losses: np.ndarray,
    faced: list[list[int]],
    played: np.ndarray,
    seed: np.ndarray,
    order_by_seed: list[int],
) -> list[Pair]:
    if round_idx == 0:
        return _initial_pairs(order_by_seed)
    groups: dict[tuple[int, int], list[int]] = {}
    for i in active:
        groups.setdefault((int(wins[i]), int(losses[i])), []).append(i)
    pairs: list[Pair] = []
    for rec in sorted(groups, key=lambda r: (-r[0], r[1])):  # most wins first
        order = _group_order(groups[rec], wins, losses, faced, seed)
        pairs.extend(_pair_group(order, played))
    return pairs


def _match_bo(record_wins: int, record_losses: int, prep: StagePrep) -> int:
    if prep.bo3_all:
        return 3
    if record_wins == prep.advance_at - 1:  # winner reaches advance_at
        return 3
    if record_losses == prep.eliminate_at - 1:  # loser reaches eliminate_at
        return 3
    return 1


# --- preparation ----------------------------------------------------------------


class StagePrep:
    """Immutable, array-based view of a StageState ready for fast simulation."""

    def __init__(self, stage_state: StageState):
        self.names: list[str] = stage_state.team_names
        self.n: int = len(self.names)
        self.index: dict[str, int] = {name: i for i, name in enumerate(self.names)}
        self.seed = np.array([t.seed for t in stage_state.teams], dtype=np.int16)
        # team indices sorted by seed (best first)
        self.order_by_seed: list[int] = sorted(range(self.n), key=lambda i: int(self.seed[i]))
        self.advance_at = stage_state.advance_at
        self.eliminate_at = stage_state.eliminate_at
        self.bo3_all = stage_state.bo3_all
        # known results -> {(lo, hi): winner_index}
        self.known: dict[Pair, int] = {}
        for r in stage_state.results:
            a, b = self.index[r.team_a], self.index[r.team_b]
            self.known[(a, b) if a < b else (b, a)] = self.index[r.winner]


# --- single simulation ----------------------------------------------------------


def simulate_stage_once(
    prep: StagePrep, map_probs: np.ndarray, rng: random.Random
) -> tuple[np.ndarray, np.ndarray]:
    """Play one full Swiss stage; return (wins, losses) int arrays of length n.

    Known results are applied deterministically; unknown matches are sampled from
    the (Bo-inflated) win probabilities.
    """
    n = prep.n
    wins = np.zeros(n, dtype=np.int8)
    losses = np.zeros(n, dtype=np.int8)
    played = np.zeros((n, n), dtype=bool)
    faced: list[list[int]] = [[] for _ in range(n)]

    round_idx = 0
    max_rounds = prep.advance_at + prep.eliminate_at  # safety bound
    while round_idx <= max_rounds:
        active = [
            i for i in range(n) if wins[i] < prep.advance_at and losses[i] < prep.eliminate_at
        ]
        if not active:
            break
        pairs = _round_pairings(
            round_idx, active, wins, losses, faced, played, prep.seed, prep.order_by_seed
        )
        for a, b in pairs:
            bo = _match_bo(int(wins[a]), int(losses[a]), prep)
            key = (a, b) if a < b else (b, a)
            w = prep.known.get(key)
            if w is None:
                p = series_win_prob(float(map_probs[a, b]), bo)
                w = a if rng.random() < p else b
            loser = b if w == a else a
            wins[w] += 1
            losses[loser] += 1
            played[a, b] = played[b, a] = True
            faced[a].append(b)
            faced[b].append(a)
        round_idx += 1
    return wins, losses


# --- deterministic live bracket (for display + obvious constraints) -------------


def live_bracket(stage_state: StageState) -> dict:
    """Replay known results to expose the current standings and the live round.

    Returns records so far and, for the first round that still has undecided
    matches, that round's pairings flagged decided/pending. This is the real
    current bracket — e.g. it shows which two teams meet in the 2-0 match.
    """
    prep = StagePrep(stage_state)
    n = prep.n
    wins = np.zeros(n, dtype=np.int8)
    losses = np.zeros(n, dtype=np.int8)
    played = np.zeros((n, n), dtype=bool)
    faced: list[list[int]] = [[] for _ in range(n)]

    rounds: list[dict] = []
    round_idx = 0
    current_round: list[dict] | None = None
    while round_idx <= prep.advance_at + prep.eliminate_at:
        active = [
            i for i in range(n) if wins[i] < prep.advance_at and losses[i] < prep.eliminate_at
        ]
        if not active:
            break
        pairs = _round_pairings(
            round_idx, active, wins, losses, faced, played, prep.seed, prep.order_by_seed
        )
        round_matches = []
        all_known = True
        for a, b in pairs:
            bo = _match_bo(int(wins[a]), int(losses[a]), prep)
            key = (a, b) if a < b else (b, a)
            w = prep.known.get(key)
            round_matches.append(
                {
                    "team_a": prep.names[a],
                    "team_b": prep.names[b],
                    "record": f"{int(wins[a])}-{int(losses[a])}",
                    "bo": bo,
                    "winner": prep.names[w] if w is not None else None,
                }
            )
            if w is None:
                all_known = False
        if not all_known:
            current_round = round_matches
            break
        # apply the fully-known round and continue
        for a, b in pairs:
            key = (a, b) if a < b else (b, a)
            w = prep.known[key]
            loser = b if w == a else a
            wins[w] += 1
            losses[loser] += 1
            played[a, b] = played[b, a] = True
            faced[a].append(b)
            faced[b].append(a)
        rounds.append({"round": round_idx + 1, "matches": round_matches})
        round_idx += 1

    standings = [
        {"team": prep.names[i], "wins": int(wins[i]), "losses": int(losses[i])}
        for i in sorted(range(n), key=lambda i: (-int(wins[i]), int(losses[i]), int(prep.seed[i])))
    ]
    return {
        "standings": standings,
        "completed_rounds": rounds,
        "current_round": current_round,  # None if the stage is fully decided
        "complete": current_round is None,
    }
