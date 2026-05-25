import type { Match, MatchResultIn, Standing } from "../types";

interface Props {
  standings: Standing[];
  currentRound: Match[] | null;
  results: MatchResultIn[];
  onSetWinner: (teamA: string, teamB: string, winner: string) => void;
  onClear: () => void;
}

export function LiveBracket({ standings, currentRound, results, onSetWinner, onClear }: Props) {
  const winnerOf = (a: string, b: string) =>
    results.find((r) => (r.team_a === a && r.team_b === b) || (r.team_a === b && r.team_b === a))
      ?.winner;

  return (
    <div className="card">
      <div className="card-head">
        <h2>Live bracket</h2>
        {results.length > 0 && (
          <button className="btn-small" onClick={onClear}>
            Clear {results.length} result{results.length > 1 ? "s" : ""}
          </button>
        )}
      </div>
      <p className="hint">
        Click a team to mark it the winner of a current-round match. Standings and picks update,
        and impossible-combo warnings refresh as paths collide.
      </p>

      {currentRound ? (
        <div className="bracket">
          {currentRound.map((m, i) => {
            const w = winnerOf(m.team_a, m.team_b);
            return (
              <div key={i} className="match">
                <span className="match-rec">
                  {m.record} · Bo{m.bo}
                </span>
                <button
                  className={`team-btn ${w === m.team_a ? "won" : w ? "lost" : ""}`}
                  onClick={() => onSetWinner(m.team_a, m.team_b, m.team_a)}
                >
                  {m.team_a}
                </button>
                <span className="vs">vs</span>
                <button
                  className={`team-btn ${w === m.team_b ? "won" : w ? "lost" : ""}`}
                  onClick={() => onSetWinner(m.team_a, m.team_b, m.team_b)}
                >
                  {m.team_b}
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <p>Stage complete — all matches decided.</p>
      )}

      <h3>Standings</h3>
      <div className="standings">
        {standings.map((s) => (
          <div key={s.team} className="standing-row">
            <span>{s.team}</span>
            <span className="record">
              {s.wins}-{s.losses}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
