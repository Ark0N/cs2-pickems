"""Human-readable rendering of the service-layer analysis dicts.

Consumes the plain dicts returned by `app.service.run_analysis` / `run_full_pickem`
so the same formatting works for the CLI and for ad-hoc inspection of API payloads.
"""

from __future__ import annotations


def format_stage(stage: dict, title: str | None = None) -> str:
    """Render one stage's analysis (prob table, picks, expected outcome, warnings)."""
    lines: list[str] = []
    label = stage.get("stage_label", f"Stage {stage['stage']}")
    title = title or f"IEM Cologne Major 2026 — Stage {stage['stage']} ({label})"
    lines.append(f"=== {title} ===")
    lines.append(f"(based on {stage['n_sims']:,} Monte Carlo simulations)")

    assumed = stage.get("assumed_advancers") or {}
    if assumed:
        for key in ("stage1", "stage2"):
            if key in assumed:
                names = ", ".join(assumed[key])
                lines.append(f"  assumed {key} advancers: {names}")
    lines.append("")

    # team_probs is already sorted by P(advance)
    lines.append(f"{'Team':<22}{'P(adv)':>8}{'P(3-0)':>8}{'P(0-3)':>8}")
    lines.append("-" * 46)
    for tp in stage["team_probs"]:
        lines.append(
            f"{tp['team']:<22}{tp['p_advance']:>8.1%}"
            f"{tp['p_three_oh']:>8.1%}{tp['p_zero_three']:>8.1%}"
        )

    pick = stage["recommendation"]["pick"]
    lines.append("\n--- Recommended picks ---")
    lines.append(f"  3-0     : {', '.join(pick['three_oh'])}")
    lines.append(f"  0-3     : {', '.join(pick['zero_three'])}")
    lines.append(f"  advance : {', '.join(pick['advance'])}")

    rec = stage["recommendation"]
    m = rec["metrics"]
    ge = m["correct_ge"]
    lines.append("\n--- Expected outcome ---")
    lines.append(f"  expected correct picks : {m['expected_correct']:.2f} / 10")
    lines.append(f"  expected points        : {rec['expected_points']:.2f}")
    lines.append(f"  P(both 3-0 right)      : {m['p_both_3_0']:.1%}")
    lines.append(f"  P(both 0-3 right)      : {m['p_both_0_3']:.1%}")
    lines.append(f"  P(>=5 correct)         : {ge[5]:.1%}")
    lines.append(f"  P(>=8 correct)         : {ge[8]:.1%}")
    if rec["feasibility_enforced"]:
        gap = rec["unconstrained_expected_points"] - rec["expected_points"]
        if gap > 1e-6:
            lines.append(
                f"  (feasibility cost      : -{gap:.2f} pts vs the impossible greedy pick)"
            )

    warns = stage["warnings"]
    if warns:
        lines.append("\n--- Warnings ---")
        for w in warns:
            tag = "IMPOSSIBLE" if w["level"] == "impossible" else "risk"
            lines.append(f"  [{tag}] {w['message']}")
    else:
        lines.append("\nNo feasibility or risk warnings. ✅")
    return "\n".join(lines)


def format_full_pickem(full: dict) -> str:
    """Render the complete multi-stage Pick'Em + playoff champion."""
    lines: list[str] = []
    lines.append("#" * 60)
    lines.append("#  IEM Cologne Major 2026 — COMPLETE PICK'EM")
    lines.append(f"#  ({full['n_sims']:,} sims/stage · objective={full['objective']})")
    lines.append("#" * 60)
    for stage in full["stages"]:
        lines.append("")
        lines.append(format_stage(stage))

    if full.get("playoffs"):
        po = full["playoffs"]
        lines.append("\n" + "=" * 46)
        lines.append("=== Playoffs (assumed Stage 3 top 8) ===")
        lines.append(f"  field   : {', '.join(full.get('playoff_field', []))}")
        lines.append(f"  CHAMPION: {po['champion_pick']}")
        top = po["team_probs"][:4]
        lines.append("  title odds:")
        for tp in top:
            lines.append(f"    {tp['team']:<20}{tp['p_champion']:>7.1%}")
        cos = po.get("cosmetics", {})
        if cos.get("mvp"):
            lines.append(f"  MVP pick: {cos['mvp']['player']} ({cos['mvp']['team']})")
        if cos.get("map"):
            lines.append(f"  Map pick: {cos['map']['pick']}")
    return "\n".join(lines)
