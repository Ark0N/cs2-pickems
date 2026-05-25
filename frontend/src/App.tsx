import { useCallback, useEffect, useRef, useState } from "react";
import { analyze, getTeams } from "./api";
import { LiveBracket } from "./components/LiveBracket";
import { Playoffs } from "./components/Playoffs";
import { ProbTable } from "./components/ProbTable";
import { Recommendation } from "./components/Recommendation";
import { TeamStrengthEditor } from "./components/TeamStrengthEditor";
import { Warnings } from "./components/Warnings";
import type { AnalyzeResponse, MatchResultIn, OddsSource, TeamInfo } from "./types";

type Tab = "swiss" | "playoffs";

function oddsSummary(o: OddsSource): string {
  if (!o.requested) return "off";
  const tag = o.keyless ? " (keyless)" : "";
  if (o.applied_matchups > 0) {
    const n = o.applied_matchups;
    return `${o.provider}${tag} · ${n} matchup${n === 1 ? "" : "s"} applied`;
  }
  return `${o.provider}${tag} · none applied yet`;
}

function Crosshair() {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <circle cx="16" cy="16" r="9" stroke="#04121f" strokeWidth="2.2" />
      <path
        d="M16 3v6M16 23v6M3 16h6M23 16h6"
        stroke="#04121f"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <circle cx="16" cy="16" r="2.2" fill="#04121f" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("swiss");
  const [teams, setTeams] = useState<TeamInfo[]>([]);
  const [overrides, setOverrides] = useState<Record<string, number>>({});
  const [results, setResults] = useState<MatchResultIn[]>([]);
  const [nSims, setNSims] = useState(100000);
  const [objective, setObjective] = useState<"category" | "ev">("category");
  const [enforceFeasible, setEnforceFeasible] = useState(true);
  const [useValve, setUseValve] = useState(true);
  const [useHltv, setUseHltv] = useState(false);
  const [useOdds, setUseOdds] = useState(false);

  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    getTeams(1).then(setTeams).catch((e) => setError(String(e)));
  }, []);

  const run = useCallback(() => {
    setLoading(true);
    analyze({
      stage: 1,
      n_sims: nSims,
      objective,
      enforce_feasible: enforceFeasible,
      use_hltv: useHltv,
      use_valve: useValve,
      use_odds: useOdds,
      results,
      rating_overrides: overrides,
    })
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [nSims, objective, enforceFeasible, useHltv, useValve, useOdds, results, overrides]);

  // debounce re-analysis when inputs change
  useEffect(() => {
    if (teams.length === 0) return;
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(run, 350);
    return () => window.clearTimeout(timer.current);
  }, [run, teams.length]);

  const setWinner = (a: string, b: string, winner: string) => {
    setResults((prev) => {
      const rest = prev.filter(
        (r) => !((r.team_a === a && r.team_b === b) || (r.team_a === b && r.team_b === a))
      );
      return [...rest, { team_a: a, team_b: b, winner }];
    });
  };

  const ds = data?.data_sources;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">
            <Crosshair />
          </span>
          <div className="brand-text">
            <span className="eyebrow">Counter-Strike 2 · Jun 2–21, 2026</span>
            <h1>IEM Cologne Major — Pick'Em Optimizer</h1>
          </div>
        </div>
        <nav className="tabs">
          <button className={tab === "swiss" ? "active" : ""} onClick={() => setTab("swiss")}>
            Swiss Stage
          </button>
          <button className={tab === "playoffs" ? "active" : ""} onClick={() => setTab("playoffs")}>
            Playoffs
          </button>
        </nav>
      </header>

      <div className="feature-strip">
        <span className="feature">
          <CheckIcon /> Monte-Carlo Swiss simulation
        </span>
        <span className="feature">
          <CheckIcon /> Impossible-combo detection
        </span>
        <span className="feature">
          <CheckIcon /> Optimal 10 picks · 2×3-0 / 6 advance / 2×0-3
        </span>
      </div>

      {error && (
        <div className="card error">
          <h2>Connection error</h2>
          {error}
          <br />
          <small>
            Is the backend running on <code>:8000</code>?{" "}
            <code>cd backend &amp;&amp; uv run uvicorn app.main:app</code>
          </small>
        </div>
      )}

      {tab === "playoffs" ? (
        <Playoffs />
      ) : (
        <>
          <section className="card controls">
            <div className="controls-head">
              <h2>Simulation</h2>
              <span className="status">
                {loading ? (
                  <>
                    <span className="spinner" /> simulating…
                  </>
                ) : data ? (
                  `${data.n_sims.toLocaleString()} sims`
                ) : (
                  ""
                )}
              </span>
            </div>

            <div className="controls-row">
              <label className="field">
                <span>Simulations</span>
                <select value={nSims} onChange={(e) => setNSims(Number(e.target.value))}>
                  <option value={5000}>5k (instant)</option>
                  <option value={15000}>15k (quick)</option>
                  <option value={50000}>50k</option>
                  <option value={100000}>100k (full)</option>
                </select>
              </label>
              <label className="field">
                <span>Objective</span>
                <select
                  value={objective}
                  onChange={(e) => setObjective(e.target.value as "category" | "ev")}
                >
                  <option value="category">category (intuitive)</option>
                  <option value="ev">ev (max expected pts)</option>
                </select>
              </label>

              <div className="switches">
                <label className="switch">
                  <input
                    type="checkbox"
                    checked={enforceFeasible}
                    onChange={(e) => setEnforceFeasible(e.target.checked)}
                  />
                  <span className="track" />
                  <span>Avoid impossible pairs</span>
                </label>
                <label className="switch">
                  <input
                    type="checkbox"
                    checked={useValve}
                    onChange={(e) => setUseValve(e.target.checked)}
                  />
                  <span className="track" />
                  <span>Valve VRS ratings (free)</span>
                </label>
                <label
                  className={`switch${useValve ? " disabled" : ""}`}
                  title={useValve ? "Valve VRS has priority — turn it off to use HLTV" : ""}
                >
                  <input
                    type="checkbox"
                    checked={useHltv}
                    disabled={useValve}
                    onChange={(e) => setUseHltv(e.target.checked)}
                  />
                  <span className="track" />
                  <span>HLTV ranking</span>
                </label>
                <label className="switch">
                  <input
                    type="checkbox"
                    checked={useOdds}
                    onChange={(e) => setUseOdds(e.target.checked)}
                  />
                  <span className="track" />
                  <span>Betting odds (keyless)</span>
                </label>
              </div>
            </div>

            {ds && (
              <div className="provenance">
                <span className="source-pill">
                  <span className="dot" />
                  <strong>Ratings</strong>
                  {ds.ratings?.label}
                  {ds.ratings?.detail ? ` · ${ds.ratings.detail}` : ""}
                </span>
                <span className="source-pill">
                  <span className={`dot${ds.odds.applied_matchups > 0 ? "" : " off"}`} />
                  <strong>Odds</strong>
                  {oddsSummary(ds.odds)}
                </span>
                {ds.ratings?.notes.map((n, i) => (
                  <span key={`r${i}`} className="source-pill warn">
                    ⚠ {n}
                  </span>
                ))}
                {ds.odds.requested && ds.odds.note && (
                  <span className="source-pill warn">⚠ {ds.odds.note}</span>
                )}
              </div>
            )}
          </section>

          {data && (
            <>
              <div className="grid">
                <Recommendation rec={data.recommendation} />
                <Warnings
                  warnings={data.warnings}
                  impossiblePairs={data.impossible_three_oh_pairs}
                />
              </div>
              <div className="grid">
                <ProbTable probs={data.team_probs} pick={data.recommendation.pick} />
                <LiveBracket
                  standings={data.standings}
                  currentRound={data.current_round}
                  results={results}
                  onSetWinner={setWinner}
                  onClear={() => setResults([])}
                />
              </div>
            </>
          )}

          {teams.length > 0 && (
            <TeamStrengthEditor
              teams={teams}
              overrides={overrides}
              onChange={(t, r) => setOverrides((p) => ({ ...p, [t]: r }))}
              onReset={() => setOverrides({})}
            />
          )}
        </>
      )}

      <footer>
        For the free Valve Pick'Em (trophies / coins). Betting odds are used only as a
        probability signal — no real-money betting.
      </footer>
    </div>
  );
}
