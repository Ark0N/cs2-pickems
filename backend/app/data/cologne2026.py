"""Seed roster for IEM Cologne Major 2026 (researched from Liquipedia).

32 teams enter across a cascading set of 16-team Swiss stages:
  - Stage 1: the 16 Stage-1 teams below.  Top 8 advance.
  - Stage 2: those 8 + the 8 Stage-2 invites.  Top 8 advance.
  - Stage 3: those 8 + the 8 Stage-3 direct invites.  Top 8 -> playoffs.

Seeds within each stage are ordered by Valve Global Standings VRS points (re-seeded
2026-05-26 from github.com/ValveSoftware/counter-strike_regional_standings). Still
PROVISIONAL: the invited field and stage split are the announced bracket and should be
re-checked against Liquipedia before the event; re-run the VRS ordering to refresh.
Teams absent from the global table (e.g. THUNDERdOWNUNDER) are seeded last in their
stage. Ratings are derived from seed (see app.ratings) until real odds / HLTV / Valve
data are loaded.
"""

from __future__ import annotations

from app.models import Team

# 8 teams seeded directly into Stage 3 (Champions stage), strongest first.
STAGE3_INVITES: list[str] = [
    "Team Vitality",
    "Natus Vincere",
    "Team Falcons",
    "The MongolZ",
    "PARIVISION",
    "Aurora Gaming",
    "FURIA",
    "MOUZ",
]

# 8 teams seeded into Stage 2.
STAGE2_INVITES: list[str] = [
    "FUT Esports",
    "Team Spirit",
    "Astralis",
    "G2 Esports",
    "Legacy",
    "paiN Gaming",
    "Monte",
    "9z Team",
]

# 16 teams that start in Stage 1.
STAGE1_INVITES: list[str] = [
    "GamerLegion",
    "B8",
    "HEROIC",
    "BetBoom Team",
    "BIG",
    "M80",
    "MIBR",
    "SINNERS Esports",
    "TYLOO",
    "Sharks Esports",
    "Gaimin Gladiators",
    "Team Liquid",
    "Lynn Vision Gaming",
    "FlyQuest",
    "NRG",
    "THUNDERdOWNUNDER",
]


def _seeded_teams(names: list[str]) -> list[Team]:
    """Assign provisional seeds 1..N in listed (standings) order."""
    return [Team(name=name, seed=i + 1) for i, name in enumerate(names)]


def stage1_teams() -> list[Team]:
    return _seeded_teams(STAGE1_INVITES)


def stage2_teams(stage1_advancers: list[str]) -> list[Team]:
    """Stage 2 = the 8 Stage-2 invites + the 8 teams that advanced from Stage 1.

    The invites are the stronger half, so they take the top seeds.
    """
    names = STAGE2_INVITES + stage1_advancers
    return _seeded_teams(names)


def stage3_teams(stage2_advancers: list[str]) -> list[Team]:
    """Stage 3 = the 8 Stage-3 direct invites + the 8 Stage-2 advancers."""
    names = STAGE3_INVITES + stage2_advancers
    return _seeded_teams(names)
