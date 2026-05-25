"""Betting-odds ingestion.

Pulls CS2 match-winner odds and converts them to fair (de-vigged) win
probabilities. Two providers ship:

- **bovada** (default, **keyless**): Bovada's public coupon JSON — no API key,
  no signup. Used purely as a probability signal (no real-money betting).
- **oddspapi**: OddsPapi free tier (REST, `?apiKey=`, `sportId=17`); needs a key.

Everything degrades gracefully: with no network/odds the client returns nothing
and the engine falls back to ranking ratings.

The transform functions (`devig_fixture`, `fixtures_to_prob_map`, `normalize_team`,
`parse_bovada_events`) are pure and unit-tested; the live HTTP layer is best-effort.
"""

from __future__ import annotations

import re

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
    """OddsPapi (keyed) provider."""

    keyless = False

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


# --- Bovada (keyless) -----------------------------------------------------------


def slugify_tournament(name: str) -> str:
    """'IEM Cologne' -> 'iem-cologne' (matches Bovada's link slugs)."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _match_moneyline(ev: dict) -> dict | None:
    """The full-match Moneyline market (period 'Game'/key '2W-12'), not per-map."""
    fallback = None
    for group in ev.get("displayGroups") or []:
        for market in group.get("markets") or []:
            if market.get("description") != "Moneyline":
                continue
            period = ((market.get("period") or {}).get("description") or "").lower()
            if "map" in period:  # per-map moneyline — ignore
                continue
            if market.get("key") == "2W-12":
                return market
            fallback = fallback or market
    return fallback


def parse_bovada_events(data, tournament: str | None = None) -> list[dict]:
    """Parse Bovada's coupon JSON into [{team_a, team_b, odd_a, odd_b}] (decimal odds).

    Keeps only each match's full-match Moneyline. The CS2 esports feed mixes several
    tournaments, so when `tournament` is given only events whose link contains its
    slug (e.g. 'iem-cologne') are kept.
    """
    slug = slugify_tournament(tournament) if tournament else None
    blocks = data if isinstance(data, list) else [data]
    out: list[dict] = []
    for block in blocks:
        for ev in block.get("events", []):
            if slug and slug not in (ev.get("link") or "").lower():
                continue
            if len(ev.get("competitors") or []) != 2:
                continue
            market = _match_moneyline(ev)
            if market is None:
                continue
            prices: dict[str, float] = {}
            for oc in market.get("outcomes") or []:
                name = oc.get("description")
                dec = (oc.get("price") or {}).get("decimal")
                try:
                    if name and dec:
                        prices[name] = float(dec)
                except (TypeError, ValueError):
                    continue
            if len(prices) != 2:
                continue
            (na, da), (nb, db) = prices.items()
            out.append({"team_a": na, "team_b": nb, "odd_a": da, "odd_b": db})
    return out


class BovadaClient:
    """Keyless betting-odds source — Bovada's public coupon JSON (no API key).

    Bovada exposes an undocumented but stable JSON feed under
    /services/sports/event/coupon/. We read the CS2 esports coupon, keep each
    match's full-match Moneyline, and de-vig the decimal prices into fair win
    probabilities. Best-effort: any network/parse failure returns [] and the
    engine falls back to ratings. Probability signal only — no real-money betting.
    """

    provider = "bovada"
    keyless = True
    URL = (
        "https://www.bovada.lv/services/sports/event/coupon/events/A/"
        "description/esports/counter-strike-2"
    )

    def __init__(self):
        self.cache = JsonCache("odds", ttl_seconds=1800)
        self.headers = {"User-Agent": settings.odds_user_agent, "Accept": "application/json"}

    @property
    def enabled(self) -> bool:
        return True  # keyless

    def fetch_fixtures(self, tournament: str = "IEM Cologne") -> list[dict]:
        cache_key = f"bovada:{slugify_tournament(tournament)}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            resp = httpx.get(self.URL, headers=self.headers, timeout=20.0)
            resp.raise_for_status()
            fixtures = parse_bovada_events(resp.json(), tournament)
        except (httpx.HTTPError, ValueError, KeyError):
            return []
        if fixtures:
            self.cache.set(cache_key, fixtures)
        return fixtures


def make_odds_client(provider: str | None = None):
    """Return the configured odds client (default: keyless Bovada); None if disabled."""
    p = (provider or settings.odds_provider or "").lower()
    if p in ("", "none"):
        return None
    if p == "oddspapi":
        return OddsClient(provider="oddspapi")
    return BovadaClient()
