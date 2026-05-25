"""Liquipedia ingestion (teams + results).

Liquipedia exposes a MediaWiki API; their policy requires a descriptive
User-Agent and modest rate limits, so responses are cached. Robust live parsing of
match results is fiddly, so this layer is best-effort with a clean fallback to the
seed roster. The `parse_results` transform is pure/tested.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.data.cache import JsonCache
from app.data.odds import normalize_team
from app.models import MatchResult


def parse_results(records: list[dict], canonical: set[str] | None = None) -> list[MatchResult]:
    """Convert raw {team1, team2, winner} records into validated MatchResults.

    Names are normalised; rows with a winner that isn't one of the two teams, or
    (when `canonical` given) teams outside the field, are dropped.
    """
    out: list[MatchResult] = []
    for r in records:
        try:
            a = normalize_team(r["team1"])
            b = normalize_team(r["team2"])
            w = normalize_team(r["winner"])
        except (KeyError, TypeError):
            continue
        if w not in (a, b):
            continue
        if canonical is not None and (a not in canonical or b not in canonical):
            continue
        out.append(MatchResult(team_a=a, team_b=b, winner=w))
    return out


class LiquipediaClient:
    BASE = "https://liquipedia.net/counterstrike/api.php"

    def __init__(self):
        self.cache = JsonCache("liquipedia", ttl_seconds=900)  # 15 min
        self.headers = {
            "User-Agent": settings.liquipedia_user_agent,
            "Accept-Encoding": "gzip",
        }

    def fetch_wikitext(self, page: str) -> str | None:
        cached = self.cache.get(page)
        if cached is not None:
            return cached
        params = {
            "action": "parse",
            "page": page,
            "prop": "wikitext",
            "format": "json",
        }
        try:
            resp = httpx.get(self.BASE, params=params, headers=self.headers, timeout=20.0)
            resp.raise_for_status()
            text = resp.json()["parse"]["wikitext"]["*"]
        except (httpx.HTTPError, KeyError, ValueError):
            return None
        self.cache.set(page, text)
        return text
