import type { Pick, TeamProb } from "../types";
import { Bar } from "./Bar";

function role(team: string, pick: Pick): string {
  if (pick.three_oh.includes(team)) return "3-0";
  if (pick.zero_three.includes(team)) return "0-3";
  if (pick.advance.includes(team)) return "adv";
  return "";
}

export function ProbTable({ probs, pick }: { probs: TeamProb[]; pick: Pick }) {
  return (
    <div className="card">
      <h2>Per-team probabilities</h2>
      <table className="prob-table">
        <thead>
          <tr>
            <th>Team</th>
            <th>Pick</th>
            <th>Advance</th>
            <th>3-0</th>
            <th>0-3</th>
          </tr>
        </thead>
        <tbody>
          {probs.map((p) => {
            const r = role(p.team, pick);
            return (
              <tr key={p.team}>
                <td className="team-name">{p.team}</td>
                <td>{r && <span className={`tag tag-${r.replace("-", "")}`}>{r}</span>}</td>
                <td><Bar value={p.p_advance} variant="advance" /></td>
                <td><Bar value={p.p_three_oh} variant="three" /></td>
                <td><Bar value={p.p_zero_three} variant="zero" /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
