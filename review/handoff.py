from review.fit_view import build_fit_view
from review.lookup import lookup_result
from review.report_view import build_report_view


def read_result(archive, kind, result_id) -> dict:
    frozen, report = lookup_result(archive, kind, result_id)
    if report is None:
        return build_fit_view(frozen)
    return build_report_view(report, frozen)
