# CS2 IEM Cologne Major 2026 — Pick'Em Optimizer

Data-driven optimizer for the **IEM Cologne Major 2026** Pick'Em Challenge (June 2–21, 2026).

It blends **betting odds** (market-implied win probabilities) with **HLTV / Valve
rankings**, simulates each 16-team Swiss stage under Valve's real **Buchholz pairing
rules** (Monte Carlo), and recommends the **optimal 10-pick set** (2× 3-0, 2× 0-3,
6× advance) per stage — while flagging **impossible combinations** (e.g. two teams that
must play each other can't both finish 3-0). Also covers the playoff bracket and cosmetic
picks.

## Tournament format (researched)

- 32 teams, **cascading 16-team Swiss stages**: Stage 1 → top 8 join Stage 2 invites →
  top 8 join Stage 3 invites → top 8 reach the 8-team single-elim playoffs (Bo3, GF Bo5).
- Inside a Swiss stage: advancement/elimination matches are **Bo3**, others **Bo1**
  (Stage 3 is all Bo3). Seeding = Valve Global Standings.
- Pick'Em per Swiss stage: pick **2 teams → 3-0**, **2 → 0-3**, **6 → advance**.

## Architecture

- `backend/` — Python (FastAPI) data ingestion + simulation + optimization engine.
- `frontend/` — Vite + React + TS interactive UI (override odds, see picks update live).
- `data/` — cached snapshots + historical-match CSV for the Elo fallback.

## Quick start (backend)

```bash
cd backend
uv sync --extra dev          # creates .venv with a modern Python + deps
uv run pytest                # run the test suite
uv run uvicorn app.main:app --reload   # start the API on :8000
```

Copy `.env.example` → `.env` and add an `ODDS_API_KEY` to enable live odds (optional —
the engine works with ranking-based ratings and manual odds entry without it).

## Status

See the build phases and during-tournament runbook in the project plan. Work is tracked
phase by phase; this README is updated as features land.
