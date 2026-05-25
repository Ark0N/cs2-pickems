# CS2 IEM Cologne Major 2026 — Pick'Em Optimizer

Data-driven optimizer for the **IEM Cologne Major 2026** Pick'Em Challenge (June 2–21, 2026).

It blends **betting odds** (market-implied win probabilities) with **HLTV / Valve
rankings**, simulates each 16-team Swiss stage under Valve's real **Buchholz pairing
rules** (Monte Carlo), and recommends the **optimal 10-pick set** (2× 3-0, 2× 0-3,
6× advance) per stage — while flagging **impossible combinations** (e.g. two teams that
must play each other can't both finish 3-0). Also covers the playoff bracket and
cosmetic picks, all in an interactive web app.

## Tournament format (researched)

- 32 teams, **cascading 16-team Swiss stages**: Stage 1 → top 8 join Stage 2 invites →
  top 8 join Stage 3 invites → top 8 reach the 8-team single-elim playoffs (Bo3, GF Bo5).
- Inside a Swiss stage: advancement/elimination matches are **Bo3**, others **Bo1**
  (Stage 3 is all Bo3). Seeding = Valve Global Standings.
- Pick'Em per Swiss stage: pick **2 teams → 3-0**, **2 → 0-3**, **6 → advance**, plus
  cosmetic skin/map/MVP picks. A 3-0 pick scores nothing if the team goes 3-1.

## How the impossible-combo detection works

The Monte Carlo runs keep the **joint outcome of every simulation**, so for any two
teams we know P(both finish 3-0). When that is 0 — because their paths must collide
(they meet in the match that decides a 3-0 spot) — the pair is flagged *impossible* and
the optimizer refuses to put both in the 3-0 slot. This updates live as results come in:

```
[IMPOSSIBLE] GamerLegion and BetBoom Team can never BOTH finish 3-0 — they play each
other right now in the 2-0 match. At most one of your two 3-0 picks can hit.
```

## Architecture

- `backend/` — Python (FastAPI) data ingestion + simulation + optimization engine.
- `frontend/` — Vite + React + TS interactive UI (override team strength, see picks live).
- `data/` — cached snapshots (gitignored).

Engine pipeline: odds/rankings → `ratings` (pairwise map probs) → `swiss` (Buchholz
pairing) → `simulate` (Monte Carlo marginals + joint samples) → `optimizer` (best 10
picks) + `feasibility` (warnings); plus `playoffs` and `cosmetics`.

## Run it

**1. Backend (API on :8000)**
```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

**2. Frontend (UI on :5173)**
```bash
cd frontend
npm install
npm run dev          # open http://localhost:5173
```

**Terminal report (no UI):**
```bash
cd backend
uv run python -m app.cli --stage 1 --sims 50000          # offline (seed-prior ratings)
uv run python -m app.cli --stage 1 --use-odds --use-hltv # live odds + HLTV ratings
```

**Tests / lint:**
```bash
cd backend && uv run pytest -q && uv run ruff check .
```

## Data sources & keys

All sources degrade gracefully — the app works offline on a transparent seed-based
rating prior. To enable live data, copy `.env.example` → `.env` (repo root):

- `ODDS_API_KEY` — OddsPapi (free tier, 250 req/mo). De-vigged odds override per-matchup
  win probabilities. Without it, ratings come from HLTV/seed only.
- HLTV ranking is scraped best-effort (Cloudflare-protected; cached, rate-limited).
- Liquipedia (MediaWiki API) provides teams/seeding/results.

> Seeds in `app/data/cologne2026.py` are **provisional** (published invite order). Refresh
> from Valve Global Standings / Liquipedia before the event.

## During-tournament runbook (June 2–21)

1. **Before Stage 1 locks:** start both servers, set objective `category`, run the full
   (100k) simulation, review the recommended 10 picks + warnings, optionally cross-check
   against majors.im / HLTV's Swiss simulator, then submit in the Valve client.
2. **As results come in:** click winners in the **Live bracket** (or pass `--results` /
   the API). Standings, probabilities, picks, and impossible-combo warnings all refresh.
   Stage 2 and Stage 3 picks open as the prior stage finishes.
3. **Before playoffs:** open the **Playoffs** tab for champion/finalist probabilities and
   the champion pick.
4. **Cosmetics:** submit the MVP suggestion; treat skin/map picks as editable meta guesses.

This optimizes the **free Valve Pick'Em** (rewards = trophies/coins/souvenirs). Betting
odds are used purely as a probability signal — no real-money betting is involved.
