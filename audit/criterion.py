from dataclasses import dataclass
from fractions import Fraction

from train.linear import dot


QuadraticForm = tuple[tuple[Fraction, ...], ...]


@dataclass(frozen=True)
class ThresholdPair:
    left: QuadraticForm
    right: QuadraticForm


def _subtract_threshold(form, metric, threshold):
    return tuple(
        tuple(energy - threshold * norm for energy, norm in zip(row, metric_row, strict=True))
        for row, metric_row in zip(form, metric, strict=True)
    )


def build_threshold_pair(basis, left_form, right_form, lo_left, lo_right) -> ThresholdPair:
    metric = tuple(tuple(dot(first, second) for second in basis) for first in basis)
    return ThresholdPair(
        _subtract_threshold(left_form, metric, lo_left),
        _subtract_threshold(right_form, metric, lo_right),
    )
