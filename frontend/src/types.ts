export interface TeamInfo {
  name: string;
  seed: number;
  rating: number;
}

export interface TeamProb {
  team: string;
  p_advance: number;
  p_three_oh: number;
  p_zero_three: number;
}

export interface Pick {
  three_oh: string[];
  zero_three: string[];
  advance: string[];
}

export interface Metrics {
  expected_points: number;
  expected_correct: number;
  p_both_3_0: number;
  p_both_0_3: number;
  p_all_6_advance: number;
  p_all_8_advancing: number;
  correct_ge: Record<string, number>;
  n_sims: number;
}

export interface Recommendation {
  pick: Pick;
  objective: string;
  expected_points: number;
  expected_correct: number;
  feasibility_enforced: boolean;
  unconstrained_expected_points: number;
  metrics: Metrics;
}

export interface Warning {
  level: "impossible" | "risk";
  message: string;
  teams: string[];
}

export interface Match {
  team_a: string;
  team_b: string;
  record: string;
  bo: number;
  winner: string | null;
}

export interface Standing {
  team: string;
  wins: number;
  losses: number;
}

export interface MatchResultIn {
  team_a: string;
  team_b: string;
  winner: string;
}

export interface AnalyzeRequest {
  stage: number;
  n_sims: number;
  objective: "category" | "ev";
  enforce_feasible: boolean;
  use_hltv: boolean;
  use_odds: boolean;
  results: MatchResultIn[];
  rating_overrides: Record<string, number>;
}

export interface AnalyzeResponse {
  stage: number;
  n_sims: number;
  teams: TeamInfo[];
  standings: Standing[];
  current_round: Match[] | null;
  complete: boolean;
  team_probs: TeamProb[];
  recommendation: Recommendation;
  warnings: Warning[];
  impossible_three_oh_pairs: [string, string][];
}

export interface PlayoffProb {
  team: string;
  p_semifinal: number;
  p_final: number;
  p_champion: number;
}

export interface Cosmetics {
  map: { pick: string; confidence: string; note: string };
  skins: Record<string, { pick: string; confidence: string }>;
  mvp: { player: string; team: string; confidence: string; note: string };
}

export interface PlayoffsResponse {
  n_sims: number;
  champion_pick: string;
  team_probs: PlayoffProb[];
  cosmetics: Cosmetics;
}
