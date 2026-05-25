# CLAUDE.md - Project Configuration

## Setup
Copy these files to your new project:
- `CLAUDE.md` → project root
- `.claude/settings.json` → `.claude/settings.json`

Then update the Project Overview section below.

---

## Project Overview
- **Project Name**: cs2-pickems
- **Description**: Data-driven **Pick'Em optimizer for the IEM Cologne Major 2026** (CS2,
  Jun 2–21 2026). Blends betting odds + HLTV/Valve rankings, simulates the 16-team Swiss
  stages under Valve's Buchholz pairing (Monte Carlo), recommends the optimal 10 picks
  (2× 3-0, 2× 0-3, 6× advance), and flags **impossible combinations** (two teams that
  must meet can't both go 3-0). Also covers the playoff bracket and cosmetic picks.
- **Tech Stack**: Python 3.11+ · FastAPI · NumPy/Pandas · httpx · pydantic · pytest/ruff
  (backend); Vite + React + TypeScript (frontend); `uv` for Python env management.
- **Last Updated**: 2026-05-25

### Layout & commands
- `backend/app/` — engine: `ratings` → `swiss` (Buchholz) → `simulate` (Monte Carlo) →
  `optimizer` + `feasibility`; plus `playoffs`, `cosmetics`, `data/` (sources
  `valve_standings`/`odds`/`hltv`/`liquipedia` + `cache` + `loader` assembler +
  `cologne2026` roster/seeds), `service.py`, `main.py` (FastAPI). `cli.py` for terminal reports.
- `frontend/src/` — React UI (`App.tsx` + `components/`) over the API.
- Run: `cd backend && uv sync --extra dev && uv run uvicorn app.main:app --reload`, then
  `cd frontend && npm install && npm run dev` (http://localhost:5173).
- Test/lint: `cd backend && uv run pytest -q && uv run ruff check .` (autofix: `ruff check --fix .`).
- One test: `uv run pytest tests/test_swiss.py -q` (file) or `uv run pytest -k impossible -q` (by name).
- Terminal report (no UI, stage 1 only): `uv run python -m app.cli --stage 1 --sims 50000`
  (add `--use-valve` / `--use-odds` / `--use-hltv`, `--objective ev`, `--allow-impossible`).
- Frontend typecheck/build: `cd frontend && npm run build` (`tsc -b && vite build`; no separate linter).
- Use `uv --directory backend run ...` if the shell's working dir isn't `backend/`.

### Architecture (big picture)
Engine pipeline (each stage consumes the previous one's output):
`data/` (roster + odds/Valve/HLTV) → **`ratings`** (Elo → per-map win-prob matrix) →
**`swiss`** (Buchholz pairing, one full stage) → **`simulate`** (Monte Carlo) →
**`optimizer`** + **`feasibility`**; plus **`playoffs`** and **`cosmetics`**.

Things that only make sense after reading several files:
- **Layering.** All business logic lives in `service.py` (`run_analysis`, `run_playoffs`).
  `main.py` (FastAPI) and `cli.py` are thin wrappers over it — add logic in `service.py`,
  not in route handlers. `report.py` formats the CLI text output.
- **Joint samples are the core idea.** `simulate.simulate_stage` returns not just marginals
  (`p_advance`, `p_three_oh`, `p_zero_three`) but the full per-sim boolean matrices
  (`s_advance`, `s_three_oh`, `s_zero_three`, shape `(n_sims, n)`). Pairwise feasibility is
  `_joint_matrix(samples) = (Fᵀ·F)/n_sims = P(i and j both happen)`. **Impossible-combo
  detection** (`feasibility.py`) and the optimizer's feasibility constraint (`optimizer.py`)
  both fall out of this matrix being `0` — so they work identically pre-event and live as
  results are entered. Don't reduce the sim to marginals.
- **Hot-path vs I/O split.** Pydantic models (`models.py`) are used only at the API/data
  boundary; the Monte Carlo inner loop (`swiss.StagePrep`, `simulate_stage_once`) runs on
  plain numpy int arrays + stdlib `random` for speed. Keep pydantic objects out of the loop.
- **Ratings priority + graceful degradation.** `data/loader.apply_ratings`: **Valve VRS →
  HLTV → seed prior** (HLTV only applies if Valve is off). Betting odds, when on, override
  *per-matchup* win probs on top of ratings (`odds_override_probs` → `build_map_probs`).
  Everything works fully offline on the transparent seed prior. Both functions return a
  provenance dict surfaced to the UI as `data_sources`.
- **Offline resilience via cache.** Every network source (Valve VRS, HLTV, odds) reads
  through `data/cache.py` (`JsonCache` — TTL'd JSON under `data/cache/<namespace>/`). Stored
  snapshots (e.g. `data/cache/valve/global.json`, `bovada_iem-cologne.json`) let runs work
  against the last fetch when offline or rate-limited; the cache also keeps HLTV scraping
  polite (Cloudflare-protected) and the keyed odds budget low.
- **Swiss rules** (`swiss.py`): a match is **Bo3** only when it would decide a team's
  advancement (3rd win) or elimination (3rd loss) — else Bo1; Stage 3 is all Bo3
  (`bo3_all`). `ratings.series_win_prob` inflates a per-map prob to Bo3/Bo5. Known
  `MatchResult`s are applied deterministically, which is how a stage resumes mid-event.
- **Stage cascade.** Only Stage 1 has a fixed 16-team field. Stages 2/3 are built from the
  previous stage's 8 advancers, so callers must pass `stage1_advancers`/`stage2_advancers`
  (16 teams total or `run_analysis` raises). This is why `/teams/{stage}` and the CLI only
  accept stage 1.
- **Optimizer objectives** (`optimizer.py`): `category` (default — best candidates per slot,
  intuitive) vs `ev` (global expected-points max); both feasibility-constrained by default.
  `scoring.ScoreWeights` defaults to 1/1/1 (maximize expected *correct* picks) and is the
  knob for real in-client point values once known.
- **Frontend** (`frontend/src/App.tsx`): single-page React; edits to controls/overrides
  debounce (350 ms) and re-`POST /analyze`. API base is the page's host on `:8000`
  (override `VITE_API_BASE`). `/analyze` responses are LRU-cached server-side by request hash.

---

## Codeman Environment

This session is managed by **Codeman** and runs within a tmux session.

**Important**: Check for `CODEMAN_MUX=1` environment variable to confirm.
- Do NOT attempt to kill your own tmux session
- The session persists across disconnects - your work is safe
- Token usage, costs, and background tasks are tracked externally

---

## Work Principles

### Autonomy
Full permissions granted. Act decisively without asking - read, write, edit, execute freely.

### Git Discipline
- **Commit after every meaningful change** - never batch unrelated work
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Commit message = what changed + why (not how)

### Documentation
- Update README.md when adding features or changing setup
- Update this file's session log after work sessions
- Keep docs in sync with code changes

### Thinking
Extended thinking is enabled. Use deep reasoning for complex architectural decisions, difficult bugs, and multi-file changes.

### Task Tracking (TodoWrite)
**ALWAYS use TodoWrite** to track tasks. This is non-negotiable for anything beyond trivial single-step work.

**When to use TodoWrite:**
- Multi-step tasks (3+ steps)
- Bug fixes requiring investigation
- Feature implementations
- Any work where progress tracking helps
- When the user provides multiple requests

**How to use it:**
1. **Before starting**: Break down the work into discrete todos
2. **During work**: Mark each todo `in_progress` before starting, `completed` when done
3. **One at a time**: Only ONE todo should be `in_progress` at any moment
4. **Immediately**: Mark todos complete the moment they're done - don't batch

**Why this matters:**
- Gives the user visibility into your progress
- Prevents forgetting tasks mid-work
- Creates accountability checkpoints
- Makes complex work manageable

**Example workflow:**
```
User: "Add user authentication with JWT"

→ TodoWrite:
  - [ ] Research existing auth patterns in codebase
  - [ ] Implement JWT token generation
  - [ ] Add login endpoint
  - [ ] Add token validation middleware
  - [ ] Add protected route example
  - [ ] Write tests

→ Mark "Research existing auth patterns" as in_progress
→ Do the research
→ Mark as completed, mark next as in_progress
→ Continue until all done
```

**Anti-patterns to avoid:**
- Starting work without creating todos first
- Having multiple todos `in_progress` simultaneously
- Batching completions at the end
- Skipping TodoWrite for "simple" multi-step tasks

---

## When to Use Agents

**Explore agent**: Codebase investigation, finding files, understanding architecture
```
"Use explore agent to find all authentication-related code"
```

**Parallel agents**: Independent tasks that don't conflict
```
"Research auth, database, and API modules in parallel using separate agents"
```

**Background execution**: Long-running operations (tests, builds)
```
"Run the test suite in the background while I continue"
```

**Sequential chaining**: When second task depends on first
```
"Use code-reviewer to find issues, then use fixer to resolve them"
```

---

## Planning Mode (Automatic)

**Automatically enter planning mode** when ANY of these conditions apply:
- Multi-file changes (3+ files affected)
- Architectural decisions
- Unclear or evolving requirements
- Risk mitigation on core systems
- New feature implementation
- Refactoring existing functionality

**Do NOT ask** whether to enter planning mode - just enter it when conditions are met.

Planning mode flow: read-only exploration → create plan → get approval → execute.

**Skip planning mode** only for:
- Single-file bug fixes
- Typo corrections
- Simple config changes
- Tasks with explicit step-by-step instructions from user

---

## Ralph Wiggum Loop (Autonomous Work Mode)

Ralph loops enable persistent, autonomous work on large tasks. When active, you continue iterating until completion criteria are met or the loop is cancelled.

### Starting a Ralph Loop
- Start: `/ralph-loop:ralph-loop`
- Cancel: `/ralph-loop:cancel-ralph`
- Help: `/ralph-loop:help`

### Time-Aware Loops

When the user specifies a **minimum duration** (e.g., "optimize for 8 hours", "work on this for 2 hours"), the loop becomes time-aware:

**At loop start:**
```bash
# Record start time
date +%s > /tmp/ralph_start_time
echo "Loop started at $(date)"
```

**Check elapsed time periodically:**
```bash
START=$(cat /tmp/ralph_start_time)
NOW=$(date +%s)
ELAPSED_HOURS=$(echo "scale=2; ($NOW - $START) / 3600" | bc)
echo "Elapsed: $ELAPSED_HOURS hours"
```

**Time-aware behavior:**
1. Complete all primary tasks from the user's prompt
2. After primary tasks done, check elapsed time
3. If minimum duration NOT reached:
   - **Do NOT output completion phrase**
   - Self-generate additional related tasks
   - Continue working until minimum time elapsed
4. Only output completion phrase when:
   - ALL primary tasks complete AND
   - Minimum duration reached (or exceeded)

**Self-generating additional tasks when time remains:**
- Code optimization (performance, readability, DRY)
- Test coverage improvements
- Edge case handling
- Error message improvements
- Documentation gaps
- Security hardening
- Accessibility improvements
- Code cleanup and dead code removal
- Dependency updates
- Type safety improvements

**Example time-aware prompt:**
```
"Optimize the API endpoints for the next 4 hours. Focus on performance first,
then code quality. Minimum runtime: 4 hours."
Completion phrase: <promise>TIME_COMPLETE</promise>
```

**Time-aware loop behavior:**
```
[Start loop, record timestamp]
[Complete primary optimization tasks - 2 hours elapsed]
[Check time: 2/4 hours - NOT done yet]
[Self-generate: "Add caching to database queries"]
[Self-generate: "Optimize N+1 queries"]
[Self-generate: "Add request batching"]
[Continue working... 4.5 hours elapsed]
[Check time: 4.5/4 hours - minimum reached]
[All tasks complete, tests pass]
<promise>TIME_COMPLETE</promise>
```

### How You Know You're in a Ralph Loop

The user started the loop with a prompt containing:
- Clear task requirements
- A **completion phrase** (e.g., `<promise>COMPLETE</promise>`)
- **Optional: minimum duration** (e.g., "for the next 4 hours")
- Iteration limits (handled by the system)

Your job: Keep working until ALL requirements are verifiably done AND minimum time reached (if specified), then output the exact completion phrase.

### Core Behaviors During Ralph Loop

**1. Work Incrementally**
- Complete one sub-task at a time
- Verify it works before moving to the next
- Don't try to do everything in one pass

**2. Commit Frequently**
- Commit after each meaningful completion
- Creates recovery points if something breaks
- Shows progress in git history
```
git add . && git commit -m "feat(auth): add token refresh endpoint"
```

**3. Self-Correct Relentlessly**
```
Loop:
  1. Implement/fix
  2. Run tests
  3. If tests fail → read error, fix, go to 1
  4. Run linter
  5. If lint errors → fix, go to 1
  6. Commit
  7. Continue to next task
```

**4. Track Progress**
Update the session log in this file as you complete tasks:
```markdown
| Date | Tasks Completed | Files Changed | Notes |
|------|-----------------|---------------|-------|
| YYYY-MM-DD | Add auth endpoint | auth.ts, routes.ts | Tests passing |
```

**5. Use Git History When Stuck**
If something isn't working:
```bash
git log --oneline -10
git diff HEAD~1
```
See what you already tried. Don't repeat failed approaches.

**6. Completion Phrase = Contract**
Only output the completion phrase (e.g., `<promise>COMPLETE</promise>`) when:
- ALL requirements from the original prompt are done
- ALL tests pass
- ALL linting passes
- Changes are committed

**Never output the completion phrase early.** The loop only ends when you say it's done.

### What Makes Good Completion Criteria

The user should provide criteria that are:
- **Verifiable**: Tests pass, lint clean, build succeeds
- **Measurable**: "5 endpoints", "all files in src/", "zero errors"
- **Binary**: Done or not done, no ambiguity

If the original prompt has vague criteria, ask clarifying questions before starting heavy work.

### Self-Correction Pattern (Include in Your Work)

```
FOR EACH TASK:
1. Implement the change
2. Run tests (npm test, pytest, go test, cargo test, etc.)
   - If fail → read error, fix, retry
3. Run linter (npm run lint, ruff, golangci-lint, etc.)
   - If fail → fix, go to step 2
4. Verify manually if needed
5. Commit with descriptive message
6. Update session log
7. Move to next task

WHEN ALL TASKS DONE:
1. Run full test suite
2. Run full lint
3. Verify build succeeds
4. Review all changes: git diff main
5. Only then output completion phrase
```

### Example: How to Think During Ralph Loop

**Original prompt**: "Add CRUD endpoints for todos with validation"

**Your approach**:
```
Task breakdown:
- [ ] GET /todos (list)
- [ ] POST /todos (create with validation)
- [ ] GET /todos/:id (single)
- [ ] PUT /todos/:id (update with validation)
- [ ] DELETE /todos/:id
- [ ] Tests for all endpoints

Starting with GET /todos...
[implement]
[test - passes]
[commit: "feat(todos): add GET /todos endpoint"]
[update session log]

Moving to POST /todos...
[implement]
[test - fails: validation not working]
[fix validation]
[test - passes]
[commit: "feat(todos): add POST /todos with validation"]
[update session log]

...continue until all done...

Final verification:
[npm test - all pass]
[npm run lint - clean]
[npm run build - succeeds]

<promise>COMPLETE</promise>
```

### When to NOT Output Completion Phrase

- Tests are failing (even one)
- Lint errors exist
- Build is broken
- You skipped a requirement
- You're unsure if something works
- **Minimum duration not reached** (for time-aware loops)

Instead: Fix the issue, verify, then complete. For time-aware loops: generate more tasks and keep improving until minimum time elapsed.

### RALPH_STATUS Block (Required During Ralph Loop)

At the **END of every response** during a Ralph Loop, output this structured status block:

```
---RALPH_STATUS---
STATUS: IN_PROGRESS | COMPLETE | BLOCKED
TASKS_COMPLETED_THIS_LOOP: <number>
FILES_MODIFIED: <number>
TESTS_STATUS: PASSING | FAILING | NOT_RUN
WORK_TYPE: IMPLEMENTATION | TESTING | DOCUMENTATION | REFACTORING
EXIT_SIGNAL: false | true
RECOMMENDATION: <one line summary of what to do next>
---END_RALPH_STATUS---
```

**Rules:**
- Output this block at the end of **every** response, no exceptions
- Set `EXIT_SIGNAL` to `true` ONLY when ALL tasks are verifiably done
- Set `STATUS` to `BLOCKED` when you need human intervention
- Do NOT continue with busy work when `EXIT_SIGNAL` should be `true`
- Do NOT forget the status block — it is required for loop tracking

### Testing Limits

- **LIMIT testing to ~20% of total effort** per loop
- PRIORITIZE: Implementation > Documentation > Tests
- Only write tests for NEW functionality
- Do NOT refactor existing tests unless broken
- Do NOT run tests repeatedly without implementing new features

### Exit Scenarios (When to Set EXIT_SIGNAL)

| Scenario | STATUS | EXIT_SIGNAL | Action |
|----------|--------|-------------|--------|
| All tasks completed, tests pass | COMPLETE | true | Output completion phrase |
| No work remaining, specs done | COMPLETE | true | Output completion phrase |
| Making normal progress | IN_PROGRESS | false | Continue to next task |
| Test-only loop (no implementation) | IN_PROGRESS | false | Warn and shift to implementation |
| Stuck on same error repeatedly | BLOCKED | false | Describe blocker, request help |
| Needs human decision/intervention | BLOCKED | false | Describe what's needed |

**Anti-patterns to avoid:**
- Setting `EXIT_SIGNAL: true` when tests are failing
- Continuing to work when all tasks are genuinely done (busy work)
- Running the same failing test repeatedly without changing approach
- Adding features not in the original specifications
- Refactoring working code instead of completing assigned tasks

---

## Code Standards

### Before Writing
- Read existing code in the area you're modifying
- Follow existing patterns and conventions
- Check for similar implementations to reference

### During Implementation
- Keep changes focused and minimal
- Don't over-engineer
- Write tests for new functionality

### After Implementation
- Run tests
- Update docs if needed
- Commit with descriptive message

---

## Hooks Awareness

This project may have hooks that auto-format code after writes or validate operations. If a tool call behaves unexpectedly, hooks are likely the cause. Continue working - they're intentional.

---

## Session Log

| Date | Tasks Completed | Files Changed | Notes |
|------|-----------------|---------------|-------|
| 2026-05-25 | Project created | CLAUDE.md | Initial setup |
| 2026-05-25 | Built full Cologne Major Pick'Em optimizer | backend/**, frontend/** | Swiss Buchholz Monte Carlo sim, optimizer with impossible-3-0 detection, playoffs + cosmetics, hybrid data layer (OddsPapi/HLTV/Liquipedia), FastAPI + React UI. 36 backend tests pass; UI builds & integrates over CORS. Ratings use a seed prior until ODDS_API_KEY/HLTV are wired; team seeds are provisional. |
| 2026-05-25 | Keyless betting odds + data-source provenance | `data/odds.py`, `data/loader.py`, `config.py`, `models.py`, `service.py`, `cli.py`, `tests/test_data.py`, `frontend/*` | Verified which `/analyze` options actually re-run the sim; found 3 inert toggles. Added a keyless **Bovada** odds provider (now default, no API key) — live IEM Cologne moneylines, de-vigged. `apply_ratings`/`odds_override_probs` return provenance; `/analyze` exposes `data_sources`, UI shows ratings/odds source + notes (HLTV disabled while Valve has priority). 39 tests pass, ruff clean, frontend builds. |
| 2026-05-26 | `/init` — documented architecture | `CLAUDE.md` | Added a "big picture" architecture subsection (service/main layering, joint-sample feasibility, hot-path vs pydantic split, ratings priority, Swiss Bo3 rules, stage cascade, optimizer objectives, frontend). Added single-test, ruff-autofix, CLI-report, and frontend-build commands. No code changes. |

---

## Current Task Queue

### Active Ralph Loop
**Status**: Not Active
**Completion Phrase**: -

### Pending Tasks
- [x] Betting odds now work **without a key** via the keyless Bovada provider (default).
      Optional: set `ODDS_API_KEY` + `ODDS_PROVIDER=oddspapi` to use OddsPapi instead.
- [ ] Refresh provisional team seeds in `backend/app/data/cologne2026.py` from Valve Global
      Standings / Liquipedia before the event.
- [ ] Confirm official Pick'Em point values in `backend/app/scoring.py` when the in-client
      challenge opens.

---

## Implementation Plans

Initial build plan (approved, executed in 9 phases): `~/.claude/plans/groovy-prancing-curry.md`.

---

## Notes & Decisions

- **Format (researched):** cascading 16-team Swiss stages → 8-team single-elim playoffs
  (QF/SF Bo3, GF Bo5); Swiss advancement/elimination matches Bo3, others Bo1 (Stage 3 all Bo3).
- **User choices:** full coverage (Swiss + playoffs + cosmetics); hybrid data (odds +
  Liquipedia + cached HLTV, all with offline fallback); interactive web app.
- **Optimizer objective:** default `category` (fill each slot with its best candidates —
  intuitive marquee 3-0 picks). `ev` (global expected-points max) is offered but sacrifices a
  borderline team into the 3-0 slot. Both stay feasibility-constrained.
- **Impossible-combo detection:** comes from Monte Carlo *joint* samples (P(both 3-0)=0),
  so it works pre-event and live as results are entered.
- **Ratings:** seed-based prior until odds/HLTV are wired; `series_win_prob` inflates per-map
  probs to Bo3/Bo5.
