from app.data.cache import JsonCache
from app.data.hltv import rank_order_to_ratings
from app.data.liquipedia import parse_results
from app.data.loader import build_map_probs, build_stage
from app.data.odds import fixtures_to_prob_map, normalize_team


def test_normalize_team_aliases():
    assert normalize_team("NAVI") == "Natus Vincere"
    assert normalize_team(" vitality ") == "Team Vitality"
    assert normalize_team("Unknown Org") == "Unknown Org"


def test_fixtures_to_prob_map_devigs_and_filters():
    fixtures = [
        {"team_a": "NAVI", "team_b": "vitality", "odd_a": 2.0, "odd_b": 2.0},
        {"team_a": "G2", "team_b": "SomeQualifier", "odd_a": 1.5, "odd_b": 2.5},
    ]
    canonical = {"Natus Vincere", "Team Vitality", "G2 Esports"}
    pm = fixtures_to_prob_map(fixtures, canonical)
    # only the fully-canonical fixture survives
    assert len(pm) == 1
    key = frozenset(("Natus Vincere", "Team Vitality"))
    assert abs(pm[key]["Natus Vincere"] - 0.5) < 1e-9
    assert abs(sum(pm[key].values()) - 1.0) < 1e-9


def test_parse_results_validates_and_normalizes():
    rows = [
        {"team1": "NAVI", "team2": "vitality", "winner": "navi"},
        {"team1": "G2", "team2": "MOUZ", "winner": "Astralis"},  # bad winner -> dropped
    ]
    res = parse_results(rows)
    assert len(res) == 1
    assert res[0].team_a == "Natus Vincere" and res[0].winner == "Natus Vincere"


def test_rank_order_to_ratings_orders_top_highest():
    r = rank_order_to_ratings(["A", "B", "C"])
    assert r["A"] > r["B"] > r["C"]


def test_build_map_probs_applies_odds_override():
    state = build_stage(1)  # offline: seed prior, no network
    names = state.team_names
    a, b = names[5], names[10]  # a normally favoured (better seed)
    override = {frozenset((a, b)): {a: 0.2, b: 0.8}}  # flip it
    m = build_map_probs(state, override)
    ia, ib = names.index(a), names.index(b)
    assert abs(m[ia, ib] - 0.2) < 1e-9
    assert abs(m[ib, ia] - 0.8) < 1e-9
    # untouched cells stay complementary
    assert abs(m[0, 1] + m[1, 0] - 1.0) < 1e-9


def test_json_cache_roundtrip_and_expiry(tmp_path):
    c = JsonCache("test_ns", ttl_seconds=1000)
    c.dir = tmp_path  # redirect away from the real cache dir
    c.set("k", {"v": 1})
    assert c.get("k") == {"v": 1}
    c.ttl = 0  # any elapsed time now counts as expired
    assert c.get("k") is None
