import type { TeamInfo } from "../types";

interface Props {
  teams: TeamInfo[];
  overrides: Record<string, number>;
  onChange: (team: string, rating: number) => void;
  onReset: () => void;
}

export function TeamStrengthEditor({ teams, overrides, onChange, onReset }: Props) {
  return (
    <div className="card">
      <div className="card-head">
        <h2>Team strength</h2>
        <button className="btn-small" onClick={onReset}>
          Reset
        </button>
      </div>
      <p className="hint">
        Drag a slider to override a team's Elo rating (1000–2100). Higher = stronger; the
        simulation and picks update automatically.
      </p>
      <div className="slider-grid">
        {teams.map((t) => {
          const rating = overrides[t.name] ?? t.rating;
          const edited = overrides[t.name] !== undefined;
          return (
            <div key={t.name} className="slider-row">
              <label className={edited ? "edited" : ""}>
                <span className="seed">#{t.seed}</span> {t.name}
              </label>
              <input
                type="range"
                min={1000}
                max={2100}
                step={10}
                value={rating}
                onChange={(e) => onChange(t.name, Number(e.target.value))}
              />
              <span className="rating-val">{Math.round(rating)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
