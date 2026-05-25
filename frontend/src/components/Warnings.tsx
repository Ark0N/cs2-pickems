import type { Warning } from "../types";

export function Warnings({
  warnings,
  impossiblePairs,
}: {
  warnings: Warning[];
  impossiblePairs: [string, string][];
}) {
  if (warnings.length === 0 && impossiblePairs.length === 0) {
    return (
      <div className="card ok">
        <h2>Feasibility</h2>
        <p>No impossible combinations or risky picks in the current recommendation. ✅</p>
      </div>
    );
  }
  return (
    <div className="card">
      <h2>Warnings</h2>
      <ul className="warn-list">
        {warnings.map((w, i) => (
          <li key={i} className={w.level === "impossible" ? "warn-impossible" : "warn-risk"}>
            <span className="warn-tag">{w.level === "impossible" ? "IMPOSSIBLE" : "risk"}</span>
            {w.message}
          </li>
        ))}
      </ul>
      {impossiblePairs.length > 0 && (
        <>
          <h3>Pairs that can never both go 3-0</h3>
          <div className="pair-list">
            {impossiblePairs.map(([a, b], i) => (
              <span key={i} className="pair">{a} ✕ {b}</span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
