"""HLTV ranking ingestion (best-effort).

HLTV has no official API and is Cloudflare-protected, so this is deliberately
gentle: one cached request, and on any failure it returns nothing and the engine
falls back to the seed prior. The rank-order -> rating transform is pure/tested.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.data.cache import JsonCache


def rank_order_to_ratings(
    ordered_names: list[str], spread: float = 500.0, base: float = 1500.0
) -> dict[str, float]:
    """Map a best->worst ranking to Elo-ish ratings (top = base + spread/2)."""
    n = len(ordered_names)
    if n == 0:
        return {}
    if n == 1:
        return {ordered_names[0]: base}
    mid = (n - 1) / 2.0
    return {name: base + spread * (mid - i) / (n - 1) for i, name in enumerate(ordered_names)}


class HLTVClient:
    def __init__(self):
        self.cache = JsonCache("hltv", ttl_seconds=21600)  # 6h
        self.headers = {"User-Agent": settings.liquipedia_user_agent}

    def world_ranking_order(self) -> list[str]:
        """Team names best->worst from HLTV's world ranking; [] if blocked."""
        cached = self.cache.get("ranking")
        if cached is not None:
            return cached
        try:
            resp = httpx.get(
                "https://www.hltv.org/ranking/teams", headers=self.headers, timeout=15.0
            )
            resp.raise_for_status()
            order = self._parse_ranking(resp.text)
        except (httpx.HTTPError, ValueError):
            return []
        if order:
            self.cache.set("ranking", order)
        return order

    @staticmethod
    def _parse_ranking(html: str) -> list[str]:
        # HLTV marks each ranked team with class="name"; order = ranking order.
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        names = [el.get_text(strip=True) for el in soup.select(".ranked-team .name")]
        return names
