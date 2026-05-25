"""Pick'Em scoring.

The objective the optimizer maximises is *expected score*. The official Valve
challenge awards a coin tier by number of correct picks, so the natural default is
to weight every correct pick equally (maximise expected correct picks). Weights are
configurable so the exact in-client point values can be matched once the challenge
opens (see plan note).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import PickEm


@dataclass(frozen=True)
class ScoreWeights:
    three_oh: float = 1.0  # per correct 3-0 pick
    zero_three: float = 1.0  # per correct 0-3 pick
    advance: float = 1.0  # per correct advancing pick


DEFAULT_WEIGHTS = ScoreWeights()


def score_outcome(
    pick: PickEm,
    three_oh: set[str],
    zero_three: set[str],
    advanced: set[str],
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> dict:
    """Score one Pick'Em against one realised stage outcome.

    A 3-0 pick only scores if the team actually finished 3-0 (not merely advanced);
    likewise 0-3. An advance pick scores if the team reached the advancing group.
    """
    correct_30 = sum(1 for t in pick.three_oh if t in three_oh)
    correct_03 = sum(1 for t in pick.zero_three if t in zero_three)
    correct_adv = sum(1 for t in pick.advance if t in advanced)
    points = (
        weights.three_oh * correct_30
        + weights.zero_three * correct_03
        + weights.advance * correct_adv
    )
    return {
        "points": points,
        "correct": correct_30 + correct_03 + correct_adv,
        "correct_3_0": correct_30,
        "correct_0_3": correct_03,
        "correct_advance": correct_adv,
    }
