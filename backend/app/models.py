"""Core domain models shared across the engine and the API boundary.

Pydantic models are used for I/O (API requests/responses, seed data). The hot
simulation path works on plain numpy arrays, not these models, for speed.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class MatchType(StrEnum):
    """Best-of format depends on what the match decides.

    In a Major Swiss stage, the matches that would give a team its 3rd win
    (advancement) or 3rd loss (elimination) are Bo3; every other match is Bo1.
    Stage 3 is all Bo3 (see StageState.bo3_all).
    """

    BO1 = "bo1"
    BO3 = "bo3"
    BO5 = "bo5"


class Team(BaseModel):
    name: str
    seed: int  # 1..N within the stage, from Valve Global Standings
    rating: float = 1500.0  # Elo-like strength; populated by the ratings layer
    region: str | None = None


class MatchResult(BaseModel):
    """A decided match, used to resume a stage mid-tournament."""

    team_a: str
    team_b: str
    winner: str

    @field_validator("winner")
    @classmethod
    def _winner_is_a_participant(cls, v: str, info):
        a, b = info.data.get("team_a"), info.data.get("team_b")
        if a is not None and b is not None and v not in (a, b):
            raise ValueError(f"winner {v!r} must be {a!r} or {b!r}")
        return v

    def key(self) -> frozenset[str]:
        return frozenset((self.team_a, self.team_b))


class StageState(BaseModel):
    """A 16-team Swiss stage, possibly partway through."""

    stage: int = Field(ge=1, le=3)
    teams: list[Team]
    results: list[MatchResult] = Field(default_factory=list)
    advance_at: int = 3  # wins needed to advance
    eliminate_at: int = 3  # losses that eliminate
    bo3_all: bool = False  # Stage 3: every match is Bo3

    @property
    def team_names(self) -> list[str]:
        return [t.name for t in self.teams]


class PickEm(BaseModel):
    """One Swiss-stage Pick'Em entry: 2x 3-0, 2x 0-3, 6x advance."""

    three_oh: list[str] = Field(min_length=2, max_length=2)
    zero_three: list[str] = Field(min_length=2, max_length=2)
    advance: list[str] = Field(min_length=6, max_length=6)

    def all_picks(self) -> list[str]:
        return [*self.three_oh, *self.zero_three, *self.advance]


class TeamProb(BaseModel):
    team: str
    p_3_0: float
    p_0_3: float
    p_advance: float


class SimResult(BaseModel):
    stage: int
    n_sims: int
    team_probs: list[TeamProb]


class Warning_(BaseModel):
    """A feasibility/risk warning surfaced to the user."""

    level: str  # "impossible" | "risk"
    message: str
    teams: list[str] = Field(default_factory=list)
