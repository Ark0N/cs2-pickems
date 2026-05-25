"""Cosmetic Pick'Em suggestions: most-used skin/map and the MVP.

These carry little hard data, so treat them as low-confidence meta guesses. The MVP
suggestion does use signal — it points at the star player of the team most likely
to go deep (driven by the simulation). Maps come from the current Active Duty pool.
Skin defaults are editable meta placeholders.
"""

from __future__ import annotations

# Best-effort star players for likely deep-run teams (edit as rosters change).
STAR_PLAYERS: dict[str, str] = {
    "Team Vitality": "ZywOo",
    "Team Spirit": "donk",
    "Natus Vincere": "w0nderful",
    "The MongolZ": "910",
    "MOUZ": "xertioN",
    "Team Falcons": "m0NESY",
    "G2 Esports": "malbsMd",
    "FaZe Clan": "frozen",
    "Aurora Gaming": "XANTARES",
    "FURIA": "yuurih",
    "PARIVISION": "Jame",
    "Astralis": "dev1ce",
}

# Current Active Duty pool; Mirage/Inferno are historically the most-played.
MAP_POOL = ["Mirage", "Inferno", "Nuke", "Ancient", "Dust2", "Anubis", "Train"]
DEFAULT_MOST_PLAYED_MAP = "Mirage"

# Editable meta placeholders for the "most-used finish" categories.
SKIN_DEFAULTS = {
    "knife": "Karambit | Doppler",
    "gloves": "Sport Gloves | Pandora's Box",
    "pistol": "USP-S | Kill Confirmed",
    "rifle": "AK-47 | Redline",
    "awp": "AWP | Asiimov",
}


def recommend_mvp(team_ranking: list[str]) -> dict:
    """Pick an MVP: the star of the strongest team that has a known star player."""
    for team in team_ranking:
        if team in STAR_PLAYERS:
            return {
                "player": STAR_PLAYERS[team],
                "team": team,
                "confidence": "medium",
                "note": "Star of the team projected to go deepest.",
            }
    top = team_ranking[0] if team_ranking else "?"
    return {
        "player": f"{top} star player",
        "team": top,
        "confidence": "low",
        "note": "No star mapped for the projected deep team — set manually.",
    }


def cosmetic_recommendations(team_ranking: list[str]) -> dict:
    """team_ranking: team names ordered strongest->weakest (e.g. by champion prob)."""
    return {
        "map": {
            "pick": DEFAULT_MOST_PLAYED_MAP,
            "confidence": "low",
            "note": f"Meta default from the Active Duty pool {MAP_POOL}.",
        },
        "skins": {k: {"pick": v, "confidence": "low"} for k, v in SKIN_DEFAULTS.items()},
        "mvp": recommend_mvp(team_ranking),
    }
