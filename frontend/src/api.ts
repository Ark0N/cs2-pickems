import type { AnalyzeRequest, AnalyzeResponse, PlayoffsResponse, TeamInfo } from "./types";

// Default to the API on the SAME host the UI was loaded from (so it works whether
// opened via localhost or the Tailscale IP). Override with VITE_API_BASE if needed.
const BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  `${window.location.protocol}//${window.location.hostname}:8000`;

async function post<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`${path} -> ${resp.status}: ${await resp.text()}`);
  return resp.json() as Promise<T>;
}

export async function getTeams(stage: number): Promise<TeamInfo[]> {
  const resp = await fetch(`${BASE}/teams/${stage}`);
  if (!resp.ok) throw new Error(`/teams/${stage} -> ${resp.status}`);
  const data = (await resp.json()) as { teams: TeamInfo[] };
  return data.teams;
}

export function analyze(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  return post<AnalyzeResponse>("/analyze", req);
}

export function playoffs(n_sims: number): Promise<PlayoffsResponse> {
  return post<PlayoffsResponse>("/playoffs", { n_sims });
}
