import type { Recommendation as Rec } from "../types";

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

export function Recommendation({ rec }: { rec: Rec }) {
  const m = rec.metrics;
  const gap = rec.unconstrained_expected_points - rec.expected_points;
  return (
    <div className="card highlight">
      <div className="rec-head">
        <h2>Recommended Pick'Em</h2>
        <div className="rec-score">
          <span className="rec-score-value">{m.expected_correct.toFixed(2)}</span>
          <span className="rec-score-label">expected correct / 10</span>
        </div>
      </div>

      <div className="picks">
        <div className="pick-card three0">
          <div className="pick-head">
            <span className="badge" /> 3-0
          </div>
          {rec.pick.three_oh.map((t) => (
            <span key={t} className="chip">
              {t}
            </span>
          ))}
        </div>
        <div className="pick-card adv">
          <div className="pick-head">
            <span className="badge" /> Advance
          </div>
          {rec.pick.advance.map((t) => (
            <span key={t} className="chip">
              {t}
            </span>
          ))}
        </div>
        <div className="pick-card zero3">
          <div className="pick-head">
            <span className="badge" /> 0-3
          </div>
          {rec.pick.zero_three.map((t) => (
            <span key={t} className="chip">
              {t}
            </span>
          ))}
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat">
          <div className="stat-value">{pct(m.correct_ge["5"] ?? 0)}</div>
          <div className="stat-label">P(≥5 correct)</div>
        </div>
        <div className="stat">
          <div className="stat-value">{pct(m.correct_ge["8"] ?? 0)}</div>
          <div className="stat-label">P(≥8 correct)</div>
        </div>
        <div className="stat">
          <div className="stat-value">{pct(m.p_all_8_advancing)}</div>
          <div className="stat-label">P(all 8 advancing)</div>
        </div>
        <div className="stat">
          <div className="stat-value">{pct(m.p_both_3_0)}</div>
          <div className="stat-label">P(both 3-0 right)</div>
        </div>
        <div className="stat">
          <div className="stat-value">{pct(m.p_both_0_3)}</div>
          <div className="stat-label">P(both 0-3 right)</div>
        </div>
      </div>

      <p className="hint">
        Objective: <code>{rec.objective}</code>
        {rec.feasibility_enforced ? " · feasibility enforced" : " · feasibility OFF"}
        {gap > 0.005 && ` · costs ${gap.toFixed(2)} pts vs the impossible greedy pick`}
      </p>
    </div>
  );
}
