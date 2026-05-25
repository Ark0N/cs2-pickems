"""Valve VRS (official Global Standings) — a free, no-key, ToS-clean ratings source.

Valve open-sources the Counter-Strike Regional/Global Standings (the very system that
seeds the Major) at github.com/ValveSoftware/counter-strike_regional_standings as dated
markdown tables. We pull the latest global table from GitHub raw (no API key, no
Cloudflare), parse team -> points, and rescale points into Elo-style ratings.

This is the recommended way to get real strength data without a betting-odds key.
"""

from __future__ import annotations

import datetime

import httpx

from app.config import settings
from app.data.cache import JsonCache
from app.data.odds import normalize_team

REPO = "ValveSoftware/counter-strike_regional_standings"


def parse_global_standings(md: str, normalize: bool = True) -> dict[str, float]:
    """Parse a `standings_global_*.md` table into {team_name: points}.

    Table shape: `| Standing | Points | Team Name | Roster |`. Header/separator rows
    are skipped because their Points cell isn't numeric.
    """
    out: dict[str, float] = {}
    for line in md.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        try:
            points = float(cells[1])
        except ValueError:
            continue  # header ("Points") or separator ("-:")
        name = normalize_team(cells[2]) if normalize else cells[2]
        out[name] = points
    return out


def points_to_ratings(
    points: dict[str, float], spread: float = 450.0, base: float = 1500.0
) -> dict[str, float]:
    """Linearly rescale a set of VRS points to Elo-style ratings.

    Rescaling is done over exactly the teams passed in (e.g. just the Major field), so
    the strength gaps within that field span the full `spread` rather than being
    compressed against the entire global list.
    """
    if not points:
        return {}
    vals = list(points.values())
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return {k: base for k in points}
    return {k: base + spread * ((v - lo) / (hi - lo) - 0.5) for k, v in points.items()}


class ValveStandingsClient:
    def __init__(self):
        self.cache = JsonCache("valve", ttl_seconds=21600)  # 6h
        self.headers = {"User-Agent": settings.liquipedia_user_agent, "Accept": "application/json"}

    def latest_global_points(self) -> dict[str, float]:
        """{team: points} from the newest global standings; {} if unreachable."""
        cached = self.cache.get("global")
        if cached is not None:
            return cached
        try:
            url = self._latest_global_url()
            if not url:
                return {}
            md = httpx.get(url, headers={"User-Agent": self.headers["User-Agent"]}, timeout=20.0)
            md.raise_for_status()
            points = parse_global_standings(md.text)
        except (httpx.HTTPError, ValueError, KeyError):
            return {}
        if points:
            self.cache.set("global", points)
        return points

    def _latest_global_url(self) -> str | None:
        """Find the raw URL of the most recent standings_global_*.md via the GitHub API."""
        year = datetime.date.today().year
        for y in (year, year - 1):
            api = f"https://api.github.com/repos/{REPO}/contents/live/{y}"
            try:
                resp = httpx.get(api, headers=self.headers, timeout=20.0)
                resp.raise_for_status()
                files = [
                    f
                    for f in resp.json()
                    if f["name"].startswith("standings_global_") and f["name"].endswith(".md")
                ]
                if files:
                    return max(files, key=lambda f: f["name"])["download_url"]
            except (httpx.HTTPError, ValueError, KeyError):
                continue
        return None
