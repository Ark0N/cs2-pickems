"""Multi-stage cascade: stages 2/3 auto-build their field from earlier stages,
and run_full_pickem chains all three Swiss stages + the playoff champion."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.service import run_analysis, run_full_pickem

client = TestClient(app)

SIMS = 1500


def _valid_pick(stage: dict) -> None:
    pick = stage["recommendation"]["pick"]
    assert len(pick["three_oh"]) == 2
    assert len(pick["zero_three"]) == 2
    assert len(pick["advance"]) == 6
    # the 10 picks are distinct teams that all exist in the stage field
    field = {t["name"] for t in stage["teams"]}
    chosen = pick["three_oh"] + pick["zero_three"] + pick["advance"]
    assert len(set(chosen)) == 10
    assert set(chosen) <= field


def test_stage2_autocascades_to_full_field():
    s2 = run_analysis(stage=2, n_sims=SIMS)
    assert len(s2["teams"]) == 16
    assert s2["stage_label"] == "Challengers Stage"
    # Stage 2 = the 8 Stage-2 invites + 8 inferred Stage-1 advancers
    assert "stage1" in s2["assumed_advancers"]
    assert len(s2["assumed_advancers"]["stage1"]) == 8
    assert "stage2" not in s2["assumed_advancers"]
    assert len(s2["expected_advancers"]) == 8
    _valid_pick(s2)


def test_stage3_autocascades_through_both_prior_stages():
    s3 = run_analysis(stage=3, n_sims=SIMS)
    assert len(s3["teams"]) == 16
    assert s3["stage_label"] == "Legends Stage"
    assert set(s3["assumed_advancers"]) == {"stage1", "stage2"}
    assert len(s3["assumed_advancers"]["stage2"]) == 8
    _valid_pick(s3)


def test_no_cascade_without_advancers_raises():
    with pytest.raises(ValueError, match="provide the 8 advancers"):
        run_analysis(stage=2, n_sims=SIMS, auto_cascade=False)


def test_explicit_advancers_skip_inference():
    s2 = run_analysis(
        stage=2, n_sims=SIMS, stage1_advancers=["B8", "M80"] + [f"X{i}" for i in range(6)]
    )
    # nothing was inferred because advancers were supplied
    assert s2["assumed_advancers"] == {}


def test_run_full_pickem_covers_every_stage_and_playoffs():
    full = run_full_pickem(n_sims=SIMS, playoff_sims=SIMS)
    assert [s["stage"] for s in full["stages"]] == [1, 2, 3]
    for s in full["stages"]:
        assert len(s["teams"]) == 16
        _valid_pick(s)
    # the playoff field is exactly Stage 3's expected top 8, and the champion is in it
    assert len(full["playoff_field"]) == 8
    assert full["playoffs"]["champion_pick"] in full["playoff_field"]


def test_full_pickem_can_skip_playoffs():
    full = run_full_pickem(n_sims=SIMS, include_playoffs=False)
    assert "playoffs" not in full
    assert len(full["stages"]) == 3


def test_analyze_endpoint_stage2():
    r = client.post("/analyze", json={"stage": 2, "n_sims": SIMS})
    assert r.status_code == 200
    body = r.json()
    assert len(body["teams"]) == 16
    assert body["assumed_advancers"]["stage1"]


def test_pickem_endpoint():
    r = client.post("/pickem", json={"n_sims": SIMS, "playoff_sims": SIMS})
    assert r.status_code == 200
    body = r.json()
    assert [s["stage_label"] for s in body["stages"]] == [
        "Opening Stage",
        "Challengers Stage",
        "Legends Stage",
    ]
    assert body["playoffs"]["champion_pick"]
