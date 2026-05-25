import type { Recommendation as Rec } from "../types";

function Pct({ v }: { v: number }) {
  return <strong>{(v * 100).toFixed(1)}%</strong>;
}

export function Recommendation({ rec }: { rec: Rec }) {
  const m = rec.metrics;
  const gap = rec.unconstrained_expected_points - rec.expected_points;
  return (
    <div className="card highlight">
      <h2>Recommended Pick'Em</h2>
      <div className="picks">
        <div className="pick-group three0">
          <h3>3-0</h3>
          {rec.pick.three_oh.map((t) => (
            <span key={t} className="chip">{t}</span>
          ))}
        </div>
        <div className="pick-group adv">
          <h3>Advance</h3>
          {rec.pick.advance.map((t) => (
            <span key={t} className="chip">{t}</span>
          ))}
        </div>
        <div className="pick-group zero3">
          <h3>0-3</h3>
          {rec.pick.zero_three.map((t) => (
            <span key={t} className="chip">{t}</span>
          ))}
        </div>
      </div>
      <div className="metrics-grid">
        <div>Expected correct: <strong>{m.expected_correct.toFixed(2)} / 10</strong></div>
        <div>P(≥5 correct): <Pct v={m.correct_ge["5"] ?? 0} /></div>
        <div>P(≥8 correct): <Pct v={m.correct_ge["8"] ?? 0} /></div>
        <div>P(both 3-0 right): <Pct v={m.p_both_3_0} /></div>
        <div>P(both 0-3 right): <Pct v={m.p_both_0_3} /></div>
        <div>P(all 8 advancing): <Pct v={m.p_all_8_advancing} /></div>
      </div>
      <p className="hint">
        Objective: <code>{rec.objective}</code>
        {rec.feasibility_enforced ? " · feasibility enforced" : " · feasibility OFF"}
        {gap > 0.005 && ` · costs ${gap.toFixed(2)} pts vs the impossible greedy pick`}
      </p>
    </div>
  );
}
