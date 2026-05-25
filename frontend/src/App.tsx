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

export default function App() {
  const [tab, setTab] = useState<Tab>("swiss");
  const [teams, setTeams] = useState<TeamInfo[]>([]);
  const [overrides, setOverrides] = useState<Record<string, number>>({});
  const [results, setResults] = useState<MatchResultIn[]>([]);
  const [nSims, setNSims] = useState(15000);
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

  return (
    <div className="app">
      <header>
        <div>
          <h1>IEM Cologne Major 2026 — Pick'Em Optimizer</h1>
          <p className="sub">
            Odds + ranking driven Swiss simulation · impossible-combo detection · optimal picks
          </p>
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

      {error && <div className="card error">⚠ {error}<br /><small>Is the backend running on :8000? <code>cd backend && uv run uvicorn app.main:app</code></small></div>}

      {tab === "playoffs" ? (
        <Playoffs />
      ) : (
        <>
          <div className="controls card">
            <label>
              Simulations
              <select value={nSims} onChange={(e) => setNSims(Number(e.target.value))}>
                <option value={5000}>5k (instant)</option>
                <option value={15000}>15k (quick)</option>
                <option value={50000}>50k</option>
                <option value={100000}>100k (full)</option>
              </select>
            </label>
            <label>
              Objective
              <select value={objective} onChange={(e) => setObjective(e.target.value as "category" | "ev")}>
                <option value="category">category (intuitive)</option>
                <option value="ev">ev (max expected pts)</option>
              </select>
            </label>
            <label className="check">
              <input type="checkbox" checked={enforceFeasible} onChange={(e) => setEnforceFeasible(e.target.checked)} />
              avoid impossible pairs
            </label>
            <label className="check">
              <input type="checkbox" checked={useValve} onChange={(e) => setUseValve(e.target.checked)} />
              Valve VRS ratings (free)
            </label>
            <label
              className={`check${useValve ? " disabled" : ""}`}
              title={useValve ? "Valve VRS has priority — turn it off to use HLTV" : ""}
            >
              <input
                type="checkbox"
                checked={useHltv}
                disabled={useValve}
                onChange={(e) => setUseHltv(e.target.checked)}
              />
              use HLTV ranking
            </label>
            <label className="check">
              <input type="checkbox" checked={useOdds} onChange={(e) => setUseOdds(e.target.checked)} />
              use betting odds (keyless)
            </label>
            <span className="status">{loading ? "simulating…" : data ? `${data.n_sims.toLocaleString()} sims` : ""}</span>
            {data?.data_sources && (
              <div className="provenance">
                <span>
                  <strong>Ratings:</strong> {data.data_sources.ratings?.label}
                  {data.data_sources.ratings?.detail ? ` — ${data.data_sources.ratings.detail}` : ""}
                </span>
                <span>
                  <strong>Odds:</strong> {oddsSummary(data.data_sources.odds)}
                </span>
                {data.data_sources.ratings?.notes.map((n, i) => (
                  <span key={`r${i}`} className="note">⚠ {n}</span>
                ))}
                {data.data_sources.odds.requested && data.data_sources.odds.note && (
                  <span className="note">⚠ {data.data_sources.odds.note}</span>
                )}
              </div>
            )}
          </div>

          {data && (
            <>
              <div className="grid">
                <Recommendation rec={data.recommendation} />
                <Warnings warnings={data.warnings} impossiblePairs={data.impossible_three_oh_pairs} />
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
        For the free Valve Pick'Em (trophies/coins). Betting odds used only as a probability
        signal — no real-money betting.
      </footer>
    </div>
  );
}
