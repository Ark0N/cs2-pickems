"""Human-readable rendering of a simulation + recommended Pick'Em."""

from __future__ import annotations

from app.feasibility import analyze_pick
from app.models import StageState
from app.optimizer import OptimizeResult, evaluate
from app.simulate import StageSimulation


def format_report(
    sim: StageSimulation,
    result: OptimizeResult,
    stage_state: StageState | None = None,
    title: str = "Pick'Em recommendation",
) -> str:
    lines: list[str] = []
    lines.append(f"=== {title} ===")
    lines.append(f"(based on {sim.n_sims:,} Monte Carlo simulations)\n")

    # probability table, sorted by P(advance)
    order = sorted(range(len(sim.names)), key=lambda i: -sim.p_advance[i])
    lines.append(f"{'Team':<22}{'P(adv)':>8}{'P(3-0)':>8}{'P(0-3)':>8}")
    lines.append("-" * 46)
    for i in order:
        lines.append(
            f"{sim.names[i]:<22}{sim.p_advance[i]:>8.1%}"
            f"{sim.p_three_oh[i]:>8.1%}{sim.p_zero_three[i]:>8.1%}"
        )

    p = result.pick
    lines.append("\n--- Recommended picks ---")
    lines.append(f"  3-0     : {', '.join(p.three_oh)}")
    lines.append(f"  0-3     : {', '.join(p.zero_three)}")
    lines.append(f"  advance : {', '.join(p.advance)}")

    metrics = evaluate(p, sim)
    lines.append("\n--- Expected outcome ---")
    lines.append(f"  expected correct picks : {metrics['expected_correct']:.2f} / 10")
    lines.append(f"  expected points        : {result.expected_points:.2f}")
    lines.append(f"  P(both 3-0 right)      : {metrics['p_both_3_0']:.1%}")
    lines.append(f"  P(both 0-3 right)      : {metrics['p_both_0_3']:.1%}")
    lines.append(f"  P(>=5 correct)         : {metrics['correct_ge'][5]:.1%}")
    lines.append(f"  P(>=8 correct)         : {metrics['correct_ge'][8]:.1%}")
    if result.feasibility_enforced:
        gap = result.unconstrained_expected_points - result.expected_points
        if gap > 1e-6:
            lines.append(
                f"  (feasibility cost      : -{gap:.2f} pts vs the impossible greedy pick)"
            )

    warns = analyze_pick(p, sim, stage_state)
    if warns:
        lines.append("\n--- Warnings ---")
        for w in warns:
            tag = "IMPOSSIBLE" if w.level == "impossible" else "risk"
            lines.append(f"  [{tag}] {w.message}")
    else:
        lines.append("\nNo feasibility or risk warnings. ✅")
    return "\n".join(lines)
