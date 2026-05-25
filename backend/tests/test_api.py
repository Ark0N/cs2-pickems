from fastapi.testclient import TestClient

from app.main import app
from app.service import run_analysis

client = TestClient(app)


def test_root_and_teams():
    assert client.get("/").status_code == 200
    r = client.get("/teams/1")
    assert r.status_code == 200
    assert len(r.json()["teams"]) == 16
    assert client.get("/teams/2").status_code == 400


def test_analyze_endpoint_returns_full_payload():
    r = client.post("/analyze", json={"stage": 1, "n_sims": 2000})
    assert r.status_code == 200
    body = r.json()
    rec = body["recommendation"]
    assert len(rec["pick"]["three_oh"]) == 2
    assert len(rec["pick"]["advance"]) == 6
    assert len(body["team_probs"]) == 16
    assert body["current_round"] is not None  # pre-event: round 1 is live
    assert "impossible_three_oh_pairs" in body


def test_analyze_with_results_advances_standings():
    teams = client.get("/teams/1").json()["teams"]
    a, b = teams[0]["name"], teams[8]["name"]  # seed 1 vs seed 9, a round-1 match
    r = client.post(
        "/analyze",
        json={
            "stage": 1,
            "n_sims": 2000,
            "results": [{"team_a": a, "team_b": b, "winner": a}],
        },
    )
    assert r.status_code == 200
    standings = {s["team"]: s for s in r.json()["standings"]}
    assert standings[a]["wins"] == 1 and standings[b]["losses"] == 1


def test_rating_override_changes_the_favourite():
    base = run_analysis(stage=1, n_sims=3000)
    top_before = base["team_probs"][0]["team"]
    underdog = base["team_probs"][-1]["team"]  # weakest team
    boosted = run_analysis(
        stage=1, n_sims=3000, rating_overrides={underdog: 2200.0}
    )
    boosted_rank = {tp["team"]: i for i, tp in enumerate(boosted["team_probs"])}
    # the boosted underdog should climb well above the bottom
    assert boosted_rank[underdog] < boosted_rank[top_before] or boosted_rank[underdog] < 8


def test_playoffs_endpoint():
    r = client.post("/playoffs", json={"n_sims": 3000})
    assert r.status_code == 200
    body = r.json()
    assert body["champion_pick"]
    assert abs(sum(t["p_champion"] for t in body["team_probs"]) - 1.0) < 1e-2  # rounded
    assert "mvp" in body["cosmetics"]
