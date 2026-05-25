"""FastAPI app — thin wrapper over app.service.

    uv run uvicorn app.main:app --reload
"""

from __future__ import annotations

import hashlib

from cachetools import LRUCache
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.data.loader import build_stage
from app.models import MatchResult
from app.service import run_analysis, run_playoffs

app = FastAPI(title="CS2 Cologne Major 2026 Pick'Em Optimizer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev: open. Lock down for any public deployment.
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache: LRUCache = LRUCache(maxsize=256)
MAX_SIMS = 200_000


# --- request models -------------------------------------------------------------


class MatchResultIn(BaseModel):
    team_a: str
    team_b: str
    winner: str


class MatchupOverrideIn(BaseModel):
    team_a: str
    team_b: str
    p_a: float = Field(ge=0.0, le=1.0)


class AnalyzeRequest(BaseModel):
    stage: int = Field(default=1, ge=1, le=3)
    n_sims: int = Field(default=20_000, ge=1_000, le=MAX_SIMS)
    objective: str = "category"
    enforce_feasible: bool = True
    use_hltv: bool = False
    use_valve: bool = False
    use_odds: bool = False
    results: list[MatchResultIn] = []
    rating_overrides: dict[str, float] = {}
    matchup_overrides: list[MatchupOverrideIn] = []
    stage1_advancers: list[str] = []
    stage2_advancers: list[str] = []
    rng_seed: int = 0


class PlayoffsRequest(BaseModel):
    team_names: list[str] | None = None
    rating_overrides: dict[str, float] = {}
    n_sims: int = Field(default=30_000, ge=1_000, le=MAX_SIMS)
    rng_seed: int = 0


# --- endpoints ------------------------------------------------------------------


@app.get("/")
def root():
    return {"app": "cs2-pickems", "event": "IEM Cologne Major 2026", "ok": True}


@app.get("/teams/{stage}")
def teams(stage: int):
    if stage != 1:
        raise HTTPException(400, "stages 2/3 are formed from previous-stage advancers")
    state = build_stage(stage)
    return {
        "stage": stage,
        "teams": [
            {"name": t.name, "seed": t.seed, "rating": round(t.rating, 1)}
            for t in state.teams
        ],
    }


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    key = hashlib.sha1(req.model_dump_json().encode()).hexdigest()
    if key in _cache:
        return _cache[key]
    try:
        out = run_analysis(
            stage=req.stage,
            n_sims=req.n_sims,
            objective=req.objective,
            enforce_feasible=req.enforce_feasible,
            use_hltv=req.use_hltv,
            use_valve=req.use_valve,
            use_odds=req.use_odds,
            results=[MatchResult(**r.model_dump()) for r in req.results],
            rating_overrides=req.rating_overrides,
            matchup_overrides=[m.model_dump() for m in req.matchup_overrides],
            stage1_advancers=req.stage1_advancers,
            stage2_advancers=req.stage2_advancers,
            rng_seed=req.rng_seed,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    _cache[key] = out
    return out


@app.post("/playoffs")
def playoffs(req: PlayoffsRequest):
    try:
        return run_playoffs(
            team_names=req.team_names,
            rating_overrides=req.rating_overrides,
            n_sims=req.n_sims,
            rng_seed=req.rng_seed,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
