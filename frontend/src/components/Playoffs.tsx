import { useEffect, useState } from "react";
import { playoffs } from "../api";
import type { PlayoffsResponse } from "../types";
import { Bar } from "./Bar";

export function Playoffs() {
  const [data, setData] = useState<PlayoffsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    playoffs(30000).then(setData).catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="card">Failed to load playoffs: {error}</div>;
  if (!data) return <div className="card">Simulating the playoff bracket…</div>;

  const c = data.cosmetics;
  return (
    <div className="grid">
      <div className="card highlight">
        <h2>Champion pick: {data.champion_pick}</h2>
        <table className="prob-table">
          <thead>
            <tr>
              <th>Team</th>
              <th>Semifinal</th>
              <th>Final</th>
              <th>Champion</th>
            </tr>
          </thead>
          <tbody>
            {data.team_probs.map((p) => (
              <tr key={p.team}>
                <td className="team-name">{p.team}</td>
                <td><Bar value={p.p_semifinal} color="#3fb27f" /></td>
                <td><Bar value={p.p_final} color="#d8a13a" /></td>
                <td><Bar value={p.p_champion} color="#c98bdb" /></td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="hint">8 teams, single elimination (QF/SF Bo3, Grand Final Bo5).</p>
      </div>

      <div className="card">
        <h2>Cosmetic picks (low confidence)</h2>
        <p>
          <strong>MVP:</strong> {c.mvp.player} ({c.mvp.team}) — {c.mvp.note}
        </p>
        <p>
          <strong>Most-played map:</strong> {c.map.pick} — {c.map.note}
        </p>
        <h3>Most-used finishes</h3>
        <ul>
          {Object.entries(c.skins).map(([k, v]) => (
            <li key={k}>
              <strong>{k}:</strong> {v.pick}
            </li>
          ))}
        </ul>
        <p className="hint">
          Skins/maps are meta guesses with little hard data — adjust before submitting.
        </p>
      </div>
    </div>
  );
}
