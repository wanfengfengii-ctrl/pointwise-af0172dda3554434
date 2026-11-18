"""Decide whether one real unit direction meets both condition thresholds.

The frozen fit stores the training center and a rational column basis of the
allowed (largest-eigenvalue) space.  For a condition its mean squared
projection along a candidate direction ``u = sum_i c_i * basis_i`` is

    (c^T M c) / (c^T G c)

where ``M`` is the mean centred outer product of the row coordinates and
``G`` is the Gram matrix of the basis columns.  ``build_threshold_pair``
subtracts ``threshold * G`` from ``M``, so a condition is met exactly when
``c^T F c >= 0`` for its shifted form ``F``.  A common physical direction
therefore exists iff some nonzero real ``c`` makes *both* shifted forms
nonnegative.  Every quantity stays rational; the only irrational step is
classifying a null direction of an indefinite 2x2 form, handled exactly with
a squared comparison so tangency (equality) counts as passing.
"""

from fractions import Fraction

from audit.criterion import QuadraticForm, ThresholdPair, build_threshold_pair
from audit.energy import compute_energy_form
from audit.request import resolve_request
from publish.commit import publish_report

# A real direction expressed as (x0 + x1*sqrt(D), y0 + y1*sqrt(D)); D >= 0.
_Direction = tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction], Fraction]


def _quadratic(form: QuadraticForm, direction: _Direction) -> tuple[Fraction, Fraction]:
    """Return (P, Q) with ``direction^T form direction == P + Q * sqrt(D)``."""
    (x0, x1), (y0, y1), D = direction
    a, b, c = form[0][0], form[0][1], form[1][1]
    x_sq = (x0 * x0 + x1 * x1 * D, 2 * x0 * x1)
    y_sq = (y0 * y0 + y1 * y1 * D, 2 * y0 * y1)
    xy = (x0 * y0 + x1 * y1 * D, x0 * y1 + x1 * y0)
    rational = a * x_sq[0] + 2 * b * xy[0] + c * y_sq[0]
    radical = a * x_sq[1] + 2 * b * xy[1] + c * y_sq[1]
    return rational, radical


def _sign(value: tuple[Fraction, Fraction], D: Fraction) -> int:
    """Exact sign of ``P + Q*sqrt(D)`` for rational P, Q and D >= 0."""
    P, Q = value
    if Q == 0 or D == 0:
        return (P > 0) - (P < 0)
    if P == 0:
        return (Q > 0) - (Q < 0)
    squared = Q * Q * D
    reference = P * P
    if P > 0:
        if Q > 0:
            return 1
        return (reference > squared) - (reference < squared)
    if Q < 0:
        return -1
    return (squared > reference) - (squared < reference)


def _classify(form: QuadraticForm) -> str:
    a, b, c = form[0][0], form[0][1], form[1][1]
    determinant = a * c - b * b
    if a >= 0 and c >= 0 and determinant >= 0:
        return 'positive'
    if a < 0 and c < 0 and determinant > 0:
        return 'negative'
    if determinant < 0:
        return 'indefinite'
    return 'negative-flat'


def _kernel(form: QuadraticForm) -> _Direction:
    a, b = form[0][0], form[0][1]
    if a != 0 or b != 0:
        return (b, Fraction(0)), (-a, Fraction(0)), Fraction(0)
    return (Fraction(1), Fraction(0)), (Fraction(0), Fraction(0)), Fraction(0)


def _null_directions(form: QuadraticForm) -> tuple[_Direction, ...]:
    a, b, c = form[0][0], form[0][1], form[1][1]
    D = b * b - a * c
    if a != 0:
        return tuple(
            ((-b, sign), (a, Fraction(0)), D) for sign in (Fraction(1), Fraction(-1))
        )
    return (
        ((Fraction(1), Fraction(0)), (Fraction(0), Fraction(0)), Fraction(0)),
        ((-c, Fraction(0)), (2 * b, Fraction(0)), Fraction(0)),
    )


def _nonnegative(form: QuadraticForm, direction: _Direction) -> bool:
    return _sign(_quadratic(form, direction), direction[2]) >= 0


def _parallel(first: _Direction, second: _Direction) -> bool:
    (ax, _), (ay, _), _ = first
    (bx, _), (by, _), _ = second
    return ax * by - ay * bx == 0


def _common_in_plane(first: QuadraticForm, second: QuadraticForm) -> bool:
    kind_first, kind_second = _classify(first), _classify(second)
    if kind_first == 'negative' or kind_second == 'negative':
        return False
    if kind_first == 'positive' or kind_second == 'positive':
        # A nonnegative-semidefinite form accepts every direction; the other
        # only needs some nonzero direction on which it is nonnegative.
        return True
    if kind_first == 'indefinite' and kind_second == 'indefinite':
        return (any(_nonnegative(second, direction) for direction in _null_directions(first))
                or any(_nonnegative(first, direction) for direction in _null_directions(second)))
    if kind_first == 'indefinite':
        # The flat negative form is nonnegative only along its kernel line.
        return _nonnegative(first, _kernel(second))
    if kind_second == 'indefinite':
        return _nonnegative(second, _kernel(first))
    return _parallel(_kernel(first), _kernel(second))


def _common_in_line(first: QuadraticForm, second: QuadraticForm) -> bool:
    return first[0][0] >= 0 and second[0][0] >= 0


def has_common_direction(pair: ThresholdPair) -> bool:
    """True iff one real direction makes both shifted forms nonnegative."""
    size = len(pair.left)
    if size != len(pair.right):
        raise ValueError('threshold forms must share a dimension')
    if size == 1:
        return _common_in_line(pair.left, pair.right)
    if size == 2:
        return _common_in_plane(pair.left, pair.right)
    raise ValueError('the allowed space must have dimension one or two')


def report(archive, fit_id, left_rev, right_rev, lo_left, lo_right, *, before_commit=None):
    request = resolve_request(archive, fit_id, left_rev, right_rev, lo_left, lo_right)
    center, basis = request.fit.center, request.fit.basis
    left_form = compute_energy_form(request.left.rows, center, basis)
    right_form = compute_energy_form(request.right.rows, center, basis)
    pair = build_threshold_pair(basis, left_form, right_form, request.lo_left, request.lo_right)
    passed = has_common_direction(pair)
    report_id = publish_report(
        archive, request.fit.fit_id, request.left.revision_id, request.right.revision_id,
        request.lo_left, request.lo_right, passed, before_commit=before_commit,
    )
    return report_id, passed
