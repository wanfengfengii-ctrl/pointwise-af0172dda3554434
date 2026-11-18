from dataclasses import dataclass
from fractions import Fraction

from measure.catalog import BatchRevision, load_revision
from measure.rationals import parse_rational
from publish.fit_records import FitRecord, load_fit


class CoverageInputError(ValueError):
    pass


@dataclass(frozen=True)
class CoverageRequest:
    fit: FitRecord
    left: BatchRevision
    right: BatchRevision
    lo_left: Fraction
    lo_right: Fraction


def _threshold(value, position):
    try:
        threshold = parse_rational(value)
    except ValueError as exc:
        raise CoverageInputError(f'{position} threshold: {exc}') from exc
    if threshold < 0:
        raise CoverageInputError(f'{position} threshold must be nonnegative')
    return threshold


def resolve_request(archive, fit_id, left_rev, right_rev, lo_left, lo_right) -> CoverageRequest:
    left_minimum = _threshold(lo_left, 'left')
    right_minimum = _threshold(lo_right, 'right')
    try:
        frozen = load_fit(archive, fit_id)
    except (LookupError, ValueError) as exc:
        raise CoverageInputError(f'fit source: {exc}') from exc
    try:
        left = load_revision(archive, left_rev)
        right = load_revision(archive, right_rev)
    except LookupError as exc:
        raise CoverageInputError(f'condition source: {exc}') from exc

    if left.unit != frozen.unit:
        raise CoverageInputError('left condition unit must equal the training unit')
    if right.unit != frozen.unit:
        raise CoverageInputError('right condition unit must equal the training unit')
    return CoverageRequest(frozen, left, right, left_minimum, right_minimum)
