"""Betting-odds ingestion.

Pulls CS2 match-winner odds and converts them to fair (de-vigged) win
probabilities. Default provider is OddsPapi (free tier, REST, `?apiKey=`,
`sportId=17` for esports). Everything degrades gracefully: with no key or no
network the client returns nothing and the engine falls back to ranking ratings.

The transform functions (`devig_fixture`, `fixtures_to_prob_map`, `normalize_team`)
are pure and unit-tested; the live HTTP/parse layer is best-effort and may need
tweaking to the provider's exact JSON shape.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.data.cache import JsonCache
from app.ratings import devig_two_way

# Bookmaker spellings -> our canonical team names.
TEAM_ALIASES: dict[str, str] = {
    "natus vincere": "Natus Vincere",
    "navi": "Natus Vincere",
    "vitality": "Team Vitality",
    "team vitality": "Team Vitality",
    "spirit": "Team Spirit",
    "team spirit": "Team Spirit",
    "the mongolz": "The MongolZ",
    "mongolz": "The MongolZ",
    "falcons": "Team Falcons",
    "team falcons": "Team Falcons",
    "mouz": "MOUZ",
    "g2": "G2 Esports",
    "g2 esports": "G2 Esports",
    "faze": "FaZe Clan",
    "liquid": "Team Liquid",
    "team liquid": "Team Liquid",
    "gamerlegion": "GamerLegion",
    "betboom": "BetBoom Team",
    "betboom team": "BetBoom Team",
    "9z": "9z Team",
    "9z team": "9z Team",
    "pain": "paiN Gaming",
    "pain gaming": "paiN Gaming",
    # Cologne field name variants (e.g. Valve VRS spellings)
    "sinners": "SINNERS Esports",
    "sharks": "Sharks Esports",
    "lynn vision": "Lynn Vision Gaming",
    "gaimin gladiators": "Gaimin Gladiators",
    "gamin gladiators": "Gaimin Gladiators",
    "fut": "FUT Esports",
    "aurora": "Aurora Gaming",
}


def normalize_team(name: str) -> str:
    """Best-effort canonicalisation of a bookmaker team name."""
    key = name.strip().lower()
    if key in TEAM_ALIASES:
        return TEAM_ALIASES[key]
    return name.strip()


def devig_fixture(odd_a: float, odd_b: float) -> tuple[float, float]:
    """Decimal odds -> fair (margin-free) probabilities for the two teams."""
    return devig_two_way(odd_a, odd_b)


def fixtures_to_prob_map(
    fixtures: list[dict], canonical: set[str] | None = None
) -> dict[frozenset[str], dict[str, float]]:
    """Turn raw fixtures into {frozenset(teamA, teamB): {teamA: pA, teamB: pB}}.

    Each fixture is {team_a, team_b, odd_a, odd_b} (decimal odds). Names are
    normalised; if `canonical` is given, only pairs fully inside it are kept. When a
    matchup appears more than once (multiple books) the latest wins.
    """
    out: dict[frozenset[str], dict[str, float]] = {}
    for fx in fixtures:
        try:
            a = normalize_team(fx["team_a"])
            b = normalize_team(fx["team_b"])
            pa, pb = devig_fixture(float(fx["odd_a"]), float(fx["odd_b"]))
        except (KeyError, ValueError, TypeError):
            continue
        if canonical is not None and (a not in canonical or b not in canonical):
            continue
        out[frozenset((a, b))] = {a: pa, b: pb}
    return out


class OddsClient:
    def __init__(self, api_key: str | None = None, provider: str | None = None):
        self.api_key = api_key if api_key is not None else settings.odds_api_key
        self.provider = provider or settings.odds_provider
        self.cache = JsonCache("odds", ttl_seconds=1800)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and self.provider not in ("", "none")

    def fetch_fixtures(self, tournament: str = "IEM Cologne") -> list[dict]:
        """Return [{team_a, team_b, odd_a, odd_b}, ...]; [] when unavailable."""
        if not self.enabled:
            return []
        cache_key = f"{self.provider}:{tournament}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            fixtures = self._fetch_oddspapi(tournament)
        except (httpx.HTTPError, ValueError, KeyError):
            return []
        self.cache.set(cache_key, fixtures)
        return fixtures

    def _fetch_oddspapi(self, tournament: str) -> list[dict]:
        # sportId=17 = esports; filter to CS2 + the tournament. Best-effort parse.
        url = "https://api.oddspapi.io/v1/odds"
        params = {"apiKey": self.api_key, "sportId": 17, "search": tournament}
        resp = httpx.get(url, params=params, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        fixtures: list[dict] = []
        for fx in data.get("fixtures", data if isinstance(data, list) else []):
            teams = fx.get("teams") or fx.get("competitors") or []
            odds = fx.get("odds") or fx.get("moneyline") or {}
            if len(teams) != 2:
                continue
            a, b = teams[0], teams[1]
            name_a = a.get("name") if isinstance(a, dict) else a
            name_b = b.get("name") if isinstance(b, dict) else b
            odd_a = (odds.get(name_a) or odds.get("home") or {}) if isinstance(odds, dict) else None
            odd_b = (odds.get(name_b) or odds.get("away") or {}) if isinstance(odds, dict) else None
            if isinstance(odd_a, dict):
                odd_a = odd_a.get("decimal")
            if isinstance(odd_b, dict):
                odd_b = odd_b.get("decimal")
            if odd_a and odd_b:
                fixtures.append(
                    {"team_a": name_a, "team_b": name_b, "odd_a": odd_a, "odd_b": odd_b}
                )
        return fixtures
