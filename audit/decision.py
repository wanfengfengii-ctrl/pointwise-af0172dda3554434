from audit.criterion import QuadraticForm, ThresholdPair, build_threshold_pair
from audit.energy import compute_energy_form
from audit.request import resolve_request
from publish.commit import publish_report


def _condition_can_pass(form: QuadraticForm) -> bool:
    first = form[0][0]
    if first >= 0:
        return True
    if len(form) == 1:
        return False
    return first * form[1][1] <= form[0][1] ** 2


def has_common_direction(pair: ThresholdPair) -> bool:
    return _condition_can_pass(pair.left) and _condition_can_pass(pair.right)


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
